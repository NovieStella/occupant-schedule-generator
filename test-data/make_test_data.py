"""
Generate SYNTHETIC illuminance CSVs for testing the CSV upload (milestone 1).

These are NOT real daylight simulation results and contain no occupant behaviour.
Values come from a crude clear-sky sun-position curve for Malmö (55.6 N, 13.0 E,
CET standard time, no daylight saving) scaled by a seeded random daily "cloudiness"
factor. Their only purpose is to exercise the parser, the statistics and the
timing / unit warnings.

Run:  python3 make_test_data.py   (writes the CSVs next to this script)
"""
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
LAT = math.radians(55.6)
LON_DEG = 13.0
STD_MERIDIAN_DEG = 15.0   # CET
PEAK_LUX = 4000.0          # arbitrary work-plane scale for a clear summer noon
rng = random.Random(42)    # fixed seed -> identical files every run


def solar_sin_elevation(day, hour_mid):
    """Sine of solar elevation (simple Cooper declination + equation of time)."""
    b = 2 * math.pi * (day - 81) / 364
    eot_min = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    decl = math.radians(23.45) * math.sin(2 * math.pi * (284 + day + 1) / 365)
    solar_time = hour_mid + (4 * (LON_DEG - STD_MERIDIAN_DEG) + eot_min) / 60
    hour_angle = math.radians(15 * (solar_time - 12))
    return (math.sin(LAT) * math.sin(decl)
            + math.cos(LAT) * math.cos(decl) * math.cos(hour_angle))


def synthetic_year():
    values = []
    for day in range(365):
        cloud = rng.uniform(0.25, 1.0)
        for hour in range(24):
            s = solar_sin_elevation(day, hour + 0.5)
            values.append(round(max(0.0, s) * PEAK_LUX * cloud, 1))
    return values


def write(name, lines):
    with open(os.path.join(HERE, name), "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


year = synthetic_year()
as_text = [f"{v:.1f}" for v in year]

# Should load
write("valid_with_header.csv", ["Illuminance (lx)"] + as_text)
write("valid_no_header.csv", as_text)
write("valid_decimal_comma.csv", [t.replace(".", ",") for t in as_text])

# Should be rejected
write("bad_8759_rows.csv", as_text[:-1])
write("bad_leap_8784_rows.csv", as_text + as_text[-24:])
text_row = as_text.copy(); text_row[4999] = "n/a"
write("bad_text_value_row5000.csv", text_row)
neg = as_text.copy(); neg[1234] = "-12.0"
write("bad_negative_row1235.csv", neg)
write("bad_two_columns_semicolon.csv", ["hour;lux"] + [f"{i};{t}" for i, t in enumerate(as_text)])
write("bad_two_columns_comma.csv", ["hour,lux"] + [f"{i},{round(v)}" for i, v in enumerate(year)])

# Should load but warn
shift = 6
write("warn_shifted_6h.csv", as_text[-shift:] + as_text[:-shift])
write("warn_daylight_factor_units.csv", [f"{v / 1000:.2f}" for v in year])

print("Wrote test CSVs to", HERE)
