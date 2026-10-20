#!/usr/bin/env python3
"""
Annual hourly daylight simulation of the Reinhart (2004) reference office, Malmö.

Room (Reinhart 2004, Solar Energy 77, 15-28, section 3.1, Fig. 5):
  3.05 m wide x 6.1 m deep x 2.74 m high, facade facing due south, no external
  obstructions, ground albedo 20 %. Reflectances: ceiling 80 %, walls 50 %, floor 20 %.
  Glazing: double low-e, visual transmittance 72 %. No blinds (out of scope in v1).
  Window: six panes digitised from Fig. 5(a) at 400 dpi (see WINDOW_PANES below).

Sensors: centre line of the room (x = 1.525 m), 0.8 m above the floor, every 0.5 m
from the window (y = 0.5 ... 6.0 m), facing up.

Method: two-phase daylight coefficients with an exact direct-sun component, the same
decomposition as the Ladybug Tools "annual-daylight" recipe:
    E = DC_total(-ab 6) x SKY_total  -  DC_direct(-ab 1) x SKY_sun  +  SUN_direct(-ab 0)
  * DC: rfluxmtx, Tregenza sky (145 patches + ground), honeybee/Radiance "detailed"
    parameters (-ab 6 -ad 65536 -lw 1.5e-5).
  * SKY: gendaymtx (Perez all-weather model) from the EPW via epw2wea; -d for sun only.
  * SUN: one 0.533 deg solar disc per sun-up hour at its actual position, radiance from
    gendaylit (Perez) with the same EPW irradiances; rcontrib -ab 0.
  Illuminance [lx] = 179 x (0.265 R + 0.670 G + 0.065 B) of the visible irradiance.

Time convention: the EPW and all outputs are in standard time (UTC+1, no daylight
saving). Row i = hour interval i:00-(i+1):00, evaluated at mid-hour (epw2wea).

Also: daylight factor under a CIE standard overcast sky, from the daylight coefficients and,
as an independent check, from rtrace with gensky -c (skip with --no-rtrace).

Requirements: pip install pyradiance honeybee-radiance  (pyradiance ships Radiance 6.0a).
Run:   python3 simulate_reinhart_office.py path/to/weather.epw [output_dir]
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np

import pyradiance
from honeybee.aperture import Aperture
from honeybee.model import Model
from honeybee.room import Room
from honeybee_radiance.modifier.material import Glass, Plastic
from honeybee_radiance.writer import model_to_rad
from ladybug_geometry.geometry3d import Face3D, Point3D

# ----------------------------------------------------------------------------- inputs
ROOM = {"width_m": 3.05, "depth_m": 6.1, "height_m": 2.74}           # Reinhart 2004, 3.1
REFLECTANCE = {"ceiling": 0.80, "walls": 0.50, "floor": 0.20}         # Reinhart 2004, 3.1
GLAZING_VT = 0.72                                                     # Reinhart 2004, 3.1
GROUND_ALBEDO = 0.20                                                  # Reinhart 2004, 3.1
# Panes digitised from Fig. 5(a) (facade 610 px = 3.05 m, 540 px = 2.74 m): x from the
# west edge of the facade, z above the floor, metres. Labelled bands in the figure:
# 0.85 m spandrel, 1.15 m main window band, 0.75 m upper band (frames included).
WINDOW_PANES = [
    # (x0, x1, z0, z1)
    (0.070, 0.970, 0.82, 1.91), (1.065, 1.965, 0.82, 1.91), (2.055, 2.955, 0.82, 1.91),   # main row
    (0.070, 0.970, 2.01, 2.62), (1.065, 1.965, 2.01, 2.62), (2.055, 2.955, 2.01, 2.62),   # upper row
]
SENSOR_X, SENSOR_Z = ROOM["width_m"] / 2, 0.8
SENSOR_DEPTHS = [round(0.5 * i, 1) for i in range(1, 13)]              # 0.5 ... 6.0 m
RAD_PARAMS_DC = "-ab 6 -ad 65536 -lw 1.5e-5"                         # honeybee "detailed"
RAD_PARAMS_DIRECT = "-ab 1 -ad 65536 -lw 1.5e-5"
RAD_PARAMS_SUN = "-ab 0 -dc 1 -dt 0 -dj 0 -ds 0 -lw 1e-7"
LUX = (47.435, 119.93, 11.635)                                        # 179 x (0.265, 0.670, 0.065)

RAD_BIN = os.path.join(os.path.dirname(pyradiance.__file__), "bin")
RAD_LIB = os.path.join(os.path.dirname(pyradiance.__file__), "lib")
ENV = dict(os.environ, PATH=RAD_BIN + os.pathsep + os.environ["PATH"], RAYPATH="." + os.pathsep + RAD_LIB)
NPROC = os.cpu_count() or 1


def run(cmd, out=None, stdin=None, cwd=None):
    """Run a Radiance shell command; return stdout text (or write to `out`)."""
    with open(stdin, "rb") if stdin else open(os.devnull, "rb") as fin:
        res = subprocess.run(cmd, shell=True, cwd=cwd, env=ENV, stdin=fin, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"{cmd}\n{res.stderr.decode()}")
    if out:
        with open(os.path.join(cwd or ".", out), "wb") as f:
            f.write(res.stdout)
    return res.stdout.decode()


def read_matrix(path):
    """Read a Radiance ASCII matrix (header, then rows of RGB triplets) -> array rows x cols x 3."""
    with open(path) as f:
        txt = f.read()
    header, _, body = txt.partition("\n\n")
    nrows = ncols = None
    for line in header.splitlines():
        if line.startswith("NROWS="): nrows = int(line.split("=")[1])
        if line.startswith("NCOLS="): ncols = int(line.split("=")[1])
    vals = np.array(body.split(), dtype=float)
    return vals.reshape(nrows, ncols, 3)


def to_lux(rgb):
    return rgb[..., 0] * LUX[0] + rgb[..., 1] * LUX[1] + rgb[..., 2] * LUX[2]


def build_model():
    room = Room.from_box("ReinhartOffice", ROOM["width_m"], ROOM["depth_m"], ROOM["height_m"])
    glass = Glass.from_single_transmittance("glazing_vt72", GLAZING_VT)
    mods = {k: Plastic.from_single_reflectance(f"{k}_{int(v * 100)}", v) for k, v in REFLECTANCE.items()}
    for face in room.faces:
        n = face.normal
        if n.z < -0.5:   face.properties.radiance.modifier = mods["floor"]
        elif n.z > 0.5:  face.properties.radiance.modifier = mods["ceiling"]
        else:            face.properties.radiance.modifier = mods["walls"]
        if abs(n.y + 1) < 1e-6:          # facade at y = 0, normal -Y = south
            for i, (x0, x1, z0, z1) in enumerate(WINDOW_PANES):
                geo = Face3D([Point3D(x0, 0, z0), Point3D(x0, 0, z1), Point3D(x1, 0, z1), Point3D(x1, 0, z0)])
                if geo.normal.y > 0:
                    geo = geo.flip()
                ap = Aperture(f"pane_{i + 1}", geo)
                ap.properties.radiance.modifier = glass
                face.add_aperture(ap)
    return Model("ReinhartOfficeMalmo", rooms=[room]), glass


SKY_RECEIVER = """#@rfluxmtx h=u u=Y
void glow groundglow 0 0 4 1 1 1 0
groundglow source ground 0 0 4 0 0 -1 180
#@rfluxmtx h=r1 u=Y
void glow skyglow 0 0 4 1 1 1 0
skyglow source skydome 0 0 4 0 0 1 180
"""


def main(epw, outdir):
    t0 = time.time()
    os.makedirs(outdir, exist_ok=True)
    work = os.path.join(outdir, "radiance")
    os.makedirs(work, exist_ok=True)

    # --- model, sensors -------------------------------------------------------
    model, glass = build_model()
    geo, mods = model_to_rad(model)
    with open(os.path.join(work, "scene.rad"), "w") as f:
        f.write(mods + "\n" + geo + "\n")
    with open(os.path.join(outdir, "model.hbjson"), "w") as f:
        json.dump(model.to_dict(), f)
    with open(os.path.join(work, "sensors.pts"), "w") as f:
        for y in SENSOR_DEPTHS:
            f.write(f"{SENSOR_X} {y} {SENSOR_Z} 0 0 1\n")
    with open(os.path.join(work, "sky.rad"), "w") as f:
        f.write(SKY_RECEIVER)
    run("oconv scene.rad", out="scene.oct", cwd=work)
    n = len(SENSOR_DEPTHS)

    # --- weather -> sky matrices ------------------------------------------------
    run(f"epw2wea {os.path.abspath(epw)} weather.wea", cwd=work)
    g = f"{GROUND_ALBEDO} {GROUND_ALBEDO} {GROUND_ALBEDO}"
    run(f"gendaymtx -m 1 -g {g} -O0 weather.wea", out="sky_total.mtx", cwd=work)
    run(f"gendaymtx -m 1 -d -g {g} -O0 weather.wea", out="sky_sun.mtx", cwd=work)

    # --- daylight coefficients ------------------------------------------------
    print("rfluxmtx total (-ab 6) ...", flush=True)
    run(f"rfluxmtx -I+ -y {n} -n {NPROC} {RAD_PARAMS_DC} - sky.rad -i scene.oct", out="dc_total.mtx", stdin=os.path.join(work, "sensors.pts"), cwd=work)
    print("rfluxmtx direct (-ab 1) ...", flush=True)
    run(f"rfluxmtx -I+ -y {n} -n {NPROC} {RAD_PARAMS_DIRECT} - sky.rad -i scene.oct", out="dc_direct.mtx", stdin=os.path.join(work, "sensors.pts"), cwd=work)
    for a, b, o in [("dc_total.mtx", "sky_total.mtx", "ill_total.mtx"), ("dc_direct.mtx", "sky_sun.mtx", "ill_direct_sky.mtx")]:
        run(f"dctimestep {a} {b}", out=o, cwd=work)
    e_total = to_lux(read_matrix(os.path.join(work, "ill_total.mtx")))          # n x 8760
    e_direct_sky = to_lux(read_matrix(os.path.join(work, "ill_direct_sky.mtx")))

    # --- exact direct sun -------------------------------------------------------
    with open(os.path.join(work, "weather.wea")) as f:
        lines = f.read().splitlines()
    hdr = {l.split()[0]: l.split()[1:] for l in lines[:6]}
    lat, lon, mer = float(hdr["latitude"][0]), float(hdr["longitude"][0]), float(hdr["time_zone"][0])
    rows = [l.split() for l in lines[6:]]
    assert len(rows) == 8760, len(rows)
    suns = []   # (hour index, rgb radiance, direction)
    for h, (mo, da, hr, dni, dhi) in enumerate(rows):
        if float(dni) <= 0:
            continue
        # Default output is visible radiance (same units as gendaymtx -O0). Passing -O0
        # explicitly segfaults in the pyradiance 1.3.0 build of gendaylit, so it is omitted.
        txt = run(f"gendaylit {mo} {da} {hr} -a {lat} -o {lon} -m {mer} -W {dni} {dhi}")
        toks = txt.split()
        if "solar" not in toks or "source" not in toks:
            continue
        i = toks.index("light")
        rgb = [float(v) for v in toks[i + 5:i + 8]]
        j = toks.index("source")
        d = [float(v) for v in toks[j + 5:j + 8]]
        if d[2] <= 0 or max(rgb) <= 0:
            continue
        suns.append((h, rgb, d))
    with open(os.path.join(work, "suns.rad"), "w") as f, open(os.path.join(work, "suns.mod"), "w") as m:
        for k, (h, rgb, d) in enumerate(suns):
            f.write(f"void light sol_{h} 0 0 3 1 1 1\nsol_{h} source sun_{h} 0 0 4 {d[0]:.6f} {d[1]:.6f} {d[2]:.6f} 0.533\n")
            m.write(f"sol_{h}\n")
    run("oconv scene.rad suns.rad", out="scene_suns.oct", cwd=work)
    print(f"rcontrib direct sun, {len(suns)} sun positions ...", flush=True)
    run(f"rcontrib -I+ -h -faa -y {n} -n {NPROC} {RAD_PARAMS_SUN} -M suns.mod scene_suns.oct", out="sun_coeff.txt", stdin=os.path.join(work, "sensors.pts"), cwd=work)
    coeff = np.loadtxt(os.path.join(work, "sun_coeff.txt")).reshape(n, len(suns), 3)
    e_sun = np.zeros((n, 8760))
    for k, (h, rgb, _) in enumerate(suns):
        e_sun[:, h] = to_lux(coeff[:, k, :] * np.array(rgb))

    ill = np.clip(e_total - e_direct_sky + e_sun, 0, None)              # n x 8760

    # --- outputs (written before the daylight-factor step) -----------------------
    names = [f"y{d:.1f}m" for d in SENSOR_DEPTHS]
    np.savetxt(os.path.join(outdir, "illuminance_centreline_all_points.csv"), ill.T, fmt="%.1f",
               delimiter=",", header=",".join(names), comments="")
    k45 = SENSOR_DEPTHS.index(4.5)
    np.savetxt(os.path.join(outdir, "illuminance_4.5m.csv"), ill[k45], fmt="%.1f", header="illuminance_lux_y4.5m", comments="")

    # --- daylight factor, CIE overcast sky ---------------------------------------
    # (a) Daylight coefficients x CIE overcast patch luminances. CIE standard overcast sky:
    #     L(alt) = Lz (1 + 2 sin alt) / 3, scaled so the unobstructed horizontal illuminance from
    #     the sky is 10 000 lx; ground patch L = albedo x 10 000 / pi. Each Tregenza patch takes the
    #     luminance at its centre altitude. (genskyvec, the usual tool, is a Perl script not
    #     shipped with pyradiance.)
    bands = [(0, 12, 30), (12, 24, 30), (24, 36, 24), (36, 48, 24), (48, 60, 18), (60, 72, 12), (72, 84, 6), (84, 90, 1)]
    lum, cosw = [], []
    for lo, hi, cnt in bands:
        a_c = np.radians(90.0 if cnt == 1 else (lo + hi) / 2)
        lum += [(1 + 2 * np.sin(a_c)) / 3] * cnt
        # exact cosine-weighted solid angle of one patch: pi (sin^2 hi - sin^2 lo) / count
        cosw += [np.pi * (np.sin(np.radians(hi)) ** 2 - np.sin(np.radians(lo)) ** 2) / cnt] * cnt
    lum = np.array(lum)
    lum *= 10000.0 / float(np.dot(lum, cosw))                           # cd/m2, 10 000 lx horizontal
    ground = GROUND_ALBEDO * 10000.0 / np.pi
    patch_rad = np.concatenate([[ground], lum]) / 179.0                 # Radiance visible radiance
    dc = read_matrix(os.path.join(work, "dc_total.mtx"))                # n x 146 x 3
    df_dc = to_lux(np.einsum("npc,p->nc", dc, patch_rad)) / 10000 * 100
    # (b) Independent check: rtrace with gensky -c (continuous sky, ambient caching), unless --no-rtrace.
    DF_RTRACE = "-ab 5 -ad 2048 -as 1024 -aa 0.1 -ar 256 -lw 1e-4"
    df_rt = None
    if "--no-rtrace" not in sys.argv:
        print("rtrace daylight factor check ...", flush=True)
        sky_cie = run("gensky 3 21 12 -c -B 55.866")                    # 10 000 lx horizontal diffuse
        with open(os.path.join(work, "sky_cie.rad"), "w") as f:
            f.write(sky_cie + "\nskyfunc glow sky_glow 0 0 4 1 1 1 0\nsky_glow source sky 0 0 4 0 0 1 180\n"
                    "skyfunc glow ground_glow 0 0 4 1 1 1 0\nground_glow source ground 0 0 4 0 0 -1 180\n")
        run("oconv scene.rad sky_cie.rad", out="scene_cie.oct", cwd=work)
        out = run(f"rtrace -I -h -n {NPROC} {DF_RTRACE} scene_cie.oct", stdin=os.path.join(work, "sensors.pts"), cwd=work)
        df_rt = to_lux(np.array(out.split(), dtype=float).reshape(n, 3)) / 10000 * 100

    lit = ill > 0
    summary = []
    for i, d in enumerate(SENSOR_DEPTHS):
        summary.append({
            "depth_m": d, "df_percent_dc": round(float(df_dc[i]), 2),
            "df_percent_rtrace": None if df_rt is None else round(float(df_rt[i]), 2),
            "annual_mean_lux": round(float(ill[i].mean()), 1),
            "daylit_mean_lux": round(float(ill[i][lit[i]].mean()), 1),
            "daylit_hours": int(lit[i].sum()),
            "max_lux": round(float(ill[i].max()), 1),
        })
    meta = {
        "created": datetime.now(timezone.utc).isoformat(),
        "purpose": "Daylight input for the Occupant Schedule Generator case study",
        "room": ROOM, "orientation": "facade faces due south (-Y), north = +Y",
        "reflectance": REFLECTANCE, "ground_albedo": GROUND_ALBEDO,
        "glazing": {"visual_transmittance": GLAZING_VT, "radiance_material": glass.to_radiance().split()},
        "window_panes_m_x0_x1_z0_z1": WINDOW_PANES,
        "glazed_area_m2": round(sum((x1 - x0) * (z1 - z0) for x0, x1, z0, z1 in WINDOW_PANES), 3),
        "facade_area_m2": round(ROOM["width_m"] * ROOM["height_m"], 3),
        "sensors": {"x_m": SENSOR_X, "z_m": SENSOR_Z, "depths_m": SENSOR_DEPTHS, "direction": "up"},
        "source": "Reinhart (2004) Solar Energy 77, 15-28, section 3.1 and Fig. 5; window digitised from Fig. 5(a)",
        "not_modelled": ["blinds (out of scope v1)", "furniture", "window frames depth and wall thickness (zero-thickness walls)",
                         "external obstructions (none, as in Reinhart 2004)"],
        "weather": {"file": os.path.basename(epw), "latitude": lat, "longitude_radiance_west_positive": lon,
                    "standard_meridian_radiance_west_positive": mer, "daylight_saving": "none (standard time)"},
        "method": "two-phase daylight coefficients with exact direct sun: DC_total(ab6) x sky - DC_direct(ab1) x sun-only sky + sun(ab0)",
        "sky_model": "Perez all-weather (gendaymtx, gendaylit), Tregenza 145 patches + ground",
        "radiance_parameters": {"dc_total": RAD_PARAMS_DC, "dc_direct": RAD_PARAMS_DIRECT, "sun": RAD_PARAMS_SUN},
        "sun_positions": len(suns),
        "daylight_factor": {"sky": "CIE standard overcast, 10 000 lx unobstructed horizontal illuminance from the sky, ground albedo 0.2",
                            "dc": "daylight coefficients (dc_total) x CIE overcast luminance at Tregenza patch centres",
                            "rtrace_check": f"gensky -c -B 55.866 with sky and ground glow; rtrace {DF_RTRACE}"},
        "software": {"radiance": run("rtrace -version").strip(), "pyradiance": pyradiance.__version__,
                     "honeybee-radiance": __import__("importlib.metadata").metadata.version("honeybee-radiance")},
        "results_by_depth": summary,
        "runtime_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(outdir, "daylight_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    for s in summary:
        print(s)
    print(f"done in {meta['runtime_s']} s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "output")
