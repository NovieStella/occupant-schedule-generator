#!/usr/bin/env python3
"""
Import test: do EnergyPlus Schedule:File objects read the exported schedules correctly?

Usage:
    pip install pyenergyplus-lbnl          # EnergyPlus engine + Python API (LBNL port)
    python3 test_schedule_file.py EXPORT.zip WEATHER.epw [work_dir]

EXPORT.zip is a "Download all (.zip)" export from the Occupant Schedule Generator.

A minimal EnergyPlus model of the case-study zone (3.05 x 6.1 x 2.74 m = 18.6 m2 floor,
200 mm concrete box, free-floating, lights 10 W/m2) reads, via Schedule:File:
  * lighting and occupancy schedules of occupants 1, 2, 50 and the last occupant (first mu file)
  * the fixed Sveby and deterministic reference schedules
and reports "Schedule Value" hourly plus the lights electricity of occupant 1's schedule.

Three runs, all with RunPeriod starting on the export's 1 January weekday:
  A  no daylight saving in the model                          -> must match the CSV exactly
  B  daylight saving ON in the model, Adjust for DST = No     -> must match the CSV exactly
  C  daylight saving ON in the model, Adjust for DST = Yes    -> expected to differ in summer
     (shows why the README says "No": the files are already in standard time)

Checks: every hour of all columns equals the CSV (hour-ending row k of EnergyPlus output =
data row k of the CSV = interval (k-1):00-k:00 standard time); lights energy of occupant 1 =
lit hours x 10 W/m2 x 18.605 m2 (3.05 x 6.1); EnergyPlus day types follow the export's weekday convention.
"""
import csv
import io
import json
import os
import shutil
import sys
import zipfile

import numpy as np
from pyenergyplus.api import EnergyPlusAPI

LPD = 10.0                       # W/m2, same as the case study
W, D, H = 3.05, 6.1, 2.74        # m, Reinhart (2004) office
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def idf_text(sched_files, start_weekday, dst_in_model, adjust_dst, epw_loc):
    lat, lon, tz, elev = epw_loc
    v = lambda pts: ",\n    ".join(f"{x},{y},{z}" for x, y, z in pts)
    surfaces = {
        "Floor": ("Floor", [(0, 0, 0), (0, D, 0), (W, D, 0), (W, 0, 0)]),
        "Roof": ("Roof", [(0, 0, H), (W, 0, H), (W, D, H), (0, D, H)]),
        "WallS": ("Wall", [(0, 0, H), (0, 0, 0), (W, 0, 0), (W, 0, H)]),
        "WallN": ("Wall", [(W, D, H), (W, D, 0), (0, D, 0), (0, D, H)]),
        "WallE": ("Wall", [(W, 0, H), (W, 0, 0), (W, D, 0), (W, D, H)]),
        "WallW": ("Wall", [(0, D, H), (0, D, 0), (0, 0, 0), (0, 0, H)]),
    }
    out = [
        "Version,25.2;",
        "SimulationControl,No,No,No,No,Yes,No,1;",
        "Building,ScheduleFileTest,0,Suburbs,0.04,0.4,FullExterior,25,6;",
        "Timestep,4;",
        "GlobalGeometryRules,UpperLeftCorner,Counterclockwise,Relative;",
        f"Site:Location,Malmo,{lat},{lon},{tz},{elev};",
        f"RunPeriod,Year,1,1,,12,31,,{WEEKDAYS[start_weekday]},No,No,No,Yes,Yes;",
        "Material,Concrete200,Rough,0.2,1.95,2240,900,0.9,0.7,0.7;",
        "Construction,C1,Concrete200;",
        "Zone,Office;",
        "ScheduleTypeLimits,Fraction,0,1,Continuous;",
    ]
    if dst_in_model:
        out.append("RunPeriodControl:DaylightSavingTime,Last Sunday in March,Last Sunday in October;")
    for name, (stype, pts) in surfaces.items():
        bc = "Ground,,NoSun,NoWind" if stype == "Floor" else "Outdoors,,SunExposed,WindExposed"
        out.append(f"BuildingSurface:Detailed,{name},{stype},C1,Office,,{bc},,4,\n    {v(pts)};")
    for s in sched_files:
        out.append(f"Schedule:File,{s['name']},Fraction,{s['path']},{s['column']},1,8760,Comma,No,60,"
                   f"{'Yes' if adjust_dst else 'No'};")
    out += [
        f"Lights,Lights_occ1,Office,{sched_files[0]['name']},Watts/Area,,{LPD},,0,0.32,0.25,1,General;",
        "Output:Variable,*,Schedule Value,Hourly;",
        "Output:Variable,*,Lights Electricity Energy,Hourly;",
        "Output:Variable,*,Site Day Type Index,Hourly;",
        "Output:Variable,*,Site Daylight Saving Time Status,Hourly;",
    ]
    return "\n".join(out) + "\n"


def read_csv_columns(text):
    rows = list(csv.reader(io.StringIO(text)))
    return rows[0], np.array(rows[1:], dtype=float)


def run_eplus(idf_path, epw, outdir):
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    api.runtime.set_console_output_status(state, False)
    code = api.runtime.run_energyplus(state, ["-r", "-w", epw, "-d", outdir, idf_path])
    api.state_manager.delete_state(state)
    err = open(os.path.join(outdir, "eplusout.err")).read()
    return code, err


def main(export_zip, epw, work):
    os.makedirs(work, exist_ok=True)
    z = zipfile.ZipFile(export_zip)
    meta = json.loads(z.read("metadata.json"))
    start_weekday = WEEKDAYS.index({"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday",
                                    "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}[meta["run"]["start_weekday_1_january"]])
    mu = meta["run"]["mu_hourly"][0]
    tag = f"mu{mu:g}"
    files = {}
    for n in (f"lighting_{tag}.csv", f"occupancy_{tag}.csv", "reference_fixed_and_deterministic.csv", "summary_occupants.csv"):
        p = os.path.join(work, n)
        with open(p, "wb") as f:
            f.write(z.read(n))
        files[n] = p

    light_hdr, light = read_csv_columns(open(files[f"lighting_{tag}.csv"]).read())
    occ_hdr, occ = read_csv_columns(open(files[f"occupancy_{tag}.csv"]).read())
    ref_hdr, ref = read_csv_columns(open(files["reference_fixed_and_deterministic.csv"]).read())
    N = len(light_hdr)
    cols = sorted({1, 2, min(50, N), N})
    scheds, expected = [], {}
    for c in cols:
        for kind, path, data, hdr in (("LIGHT", files[f"lighting_{tag}.csv"], light, light_hdr),
                                      ("OCC", files[f"occupancy_{tag}.csv"], occ, occ_hdr)):
            name = f"{kind}_{hdr[c - 1]}"
            scheds.append({"name": name, "path": path, "column": c})
            expected[name.upper()] = data[:, c - 1]
    for c, label in ((1, "REF_FIXED"), (2, "REF_DETERMINISTIC")):
        scheds.append({"name": label, "path": files["reference_fixed_and_deterministic.csv"], "column": c})
        expected[label] = ref[:, c - 1]

    with open(epw) as f:
        loc = f.readline().strip().split(",")
    epw_loc = (loc[6], loc[7], loc[8], loc[9])

    lit_occ1 = None
    with open(files["summary_occupants.csv"]) as f:
        for r in csv.DictReader(f):
            if r["occupant"] == light_hdr[0] and abs(float(r["mu_hourly"]) - mu) < 1e-9:
                lit_occ1 = float(r["lit_hours"])

    report = {"energyplus_engine": "pyenergyplus-lbnl (EnergyPlus 25.2.0 API)", "export": os.path.basename(export_zip),
              "start_weekday": WEEKDAYS[start_weekday], "schedules_tested": [s["name"] for s in scheds], "runs": {}}
    for run, (dst, adjust) in {"A_no_dst": (False, False), "B_dst_adjust_no": (True, False), "C_dst_adjust_yes": (True, True)}.items():
        d = os.path.join(work, run)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        idf = os.path.join(d, "in.idf")
        with open(idf, "w") as f:
            f.write(idf_text(scheds, start_weekday, dst, adjust, epw_loc))
        code, err = run_eplus(idf, epw, d)
        severe = [l for l in err.splitlines() if "** Severe" in l or "**  Fatal" in l]
        out_rows = list(csv.reader(open(os.path.join(d, "eplusout.csv"))))
        hdr, body = out_rows[0], out_rows[1:]
        res = {"exit_code": code, "rows": len(body), "severe_or_fatal": severe[:5], "columns": {}}
        for name, exp in expected.items():
            col = [i for i, h in enumerate(hdr) if h.startswith(f"{name}:Schedule Value")]
            if not col:
                res["columns"][name] = "not reported"
                continue
            got = np.array([float(r[col[0]]) for r in body])
            diff = np.nonzero(np.abs(got - exp) > 1e-9)[0]
            res["columns"][name] = {"hours_differing": int(len(diff)),
                                    "first_differences": [{"row": int(i) + 1, "eplus_time": body[i][0].strip(), "csv": exp[i], "eplus": got[i]} for i in diff[:3]]}
        lc = [i for i, h in enumerate(hdr) if "Lights Electricity Energy" in h]
        if lc:
            kwh = sum(float(r[lc[0]]) for r in body) / 3.6e6
            res["lights_kwh_occ1"] = round(kwh, 3)
            res["expected_kwh_occ1"] = round(lit_occ1 * LPD * W * D / 1000, 3) if lit_occ1 is not None else None
        dti = [i for i, h in enumerate(hdr) if "Site Day Type Index" in h]
        if dti:
            day_types = [int(float(body[t][dti[0]])) for t in range(12, 8760, 24)]   # E+: 1 = Sunday ... 7 = Saturday
            exp_types = [((start_weekday + d) % 7 + 1) % 7 + 1 for d in range(365)]
            res["day_type_mismatches"] = sum(a != b for a, b in zip(day_types, exp_types))
        dst_col = [i for i, h in enumerate(hdr) if "Daylight Saving Time Status" in h]
        if dst_col:
            st = [float(r[dst_col[0]]) for r in body]
            on = [i for i, v in enumerate(st) if v > 0.5]
            res["dst_hours_in_model"] = len(on)
            res["dst_first_last_eplus_time"] = [body[on[0]][0].strip(), body[on[-1]][0].strip()] if on else None
        res["sample_rows"] = [body[i][0].strip() for i in (0, 7, 8, 4367)]
        report["runs"][run] = res

    with open(os.path.join(work, "schedule_file_test_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=float)
    print(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "eplus_work")
