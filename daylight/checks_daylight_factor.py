#!/usr/bin/env python3
"""
Checks on the daylight factor (DF) gap: 8.5 % at 1.5 m simulated vs 11 % in Reinhart (2004).
Run after simulate_reinhart_office.py (uses output/radiance/scene.rad):
    python3 checks_daylight_factor.py [output_dir]

1. Glass: transmissivity converted from 72 % transmittance (not 0.72 entered directly), and
   Radiance's normal-incidence transmittance of that material measured with rtrace.
2. Convergence: DF at 1.5 m with increasing ambient bounces (-ab 6 ... 12).
3. Window variants: how much glazing would be needed to reach 11 % (explanation only; the model
   keeps the window as drawn in Fig. 5(a)).
"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0], "--no-rtrace"] + sys.argv[1:]
import simulate_reinhart_office as s  # noqa: E402
from honeybee_radiance.writer import model_to_rad  # noqa: E402

out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "output")
src = os.path.join(out, "radiance")
work = os.path.join(out, "checks")
os.makedirs(work, exist_ok=True)


def cie_overcast_patch_radiance():
    """CIE standard overcast, 10 000 lx horizontal from the sky, ground albedo; Tregenza + ground."""
    bands = [(0, 12, 30), (12, 24, 30), (24, 36, 24), (36, 48, 24), (48, 60, 18), (60, 72, 12), (72, 84, 6), (84, 90, 1)]
    lum, cosw = [], []
    for lo, hi, c in bands:
        a = np.radians(90 if c == 1 else (lo + hi) / 2)
        lum += [(1 + 2 * np.sin(a)) / 3] * c
        cosw += [np.pi * (np.sin(np.radians(hi)) ** 2 - np.sin(np.radians(lo)) ** 2) / c] * c
    lum = np.array(lum)
    lum *= 10000 / np.dot(lum, cosw)
    return np.concatenate([[s.GROUND_ALBEDO * 10000 / np.pi], lum]) / 179


PR = cie_overcast_patch_radiance()


def df_at(scene_dir, depths, params):
    with open(os.path.join(scene_dir, "pts.pts"), "w") as f:
        f.write("".join(f"{s.SENSOR_X} {y} {s.SENSOR_Z} 0 0 1\n" for y in depths))
    with open(os.path.join(scene_dir, "sky.rad"), "w") as f:
        f.write(s.SKY_RECEIVER)
    s.run("oconv scene.rad", out="scene.oct", cwd=scene_dir)
    s.run(f"rfluxmtx -I+ -y {len(depths)} -n {s.NPROC} {params} - sky.rad -i scene.oct", out="dc.mtx",
          stdin=os.path.join(scene_dir, "pts.pts"), cwd=scene_dir)
    return s.to_lux(np.einsum("npc,p->nc", s.read_matrix(os.path.join(scene_dir, "dc.mtx")), PR)) / 100


# 1. glass ---------------------------------------------------------------------
scene = open(os.path.join(src, "scene.rad")).read()
glass_def = scene[scene.index("void glass glazing_vt72"):].split("\n\n")[0]
tn = float(glass_def.split()[-1])
d = os.path.join(work, "glass")
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "with.rad"), "w") as f:
    f.write(glass_def + "\nvoid light sun_mat 0 0 3 1e6 1e6 1e6\nsun_mat source sun 0 0 4 0 0 1 0.533\n"
            "glazing_vt72 polygon pane 0 0 12 -50 -50 1 50 -50 1 50 50 1 -50 50 1\n")
with open(os.path.join(d, "without.rad"), "w") as f:
    f.write("void light sun_mat 0 0 3 1e6 1e6 1e6\nsun_mat source sun 0 0 4 0 0 1 0.533\n")
vals = []
for name in ("with", "without"):
    s.run(f"oconv {name}.rad", out=f"{name}.oct", cwd=d)
    with open(os.path.join(d, "pt.pts"), "w") as f:
        f.write("0 0 0 0 0 1\n")
    vals.append(float(s.run(f"rtrace -I -h -ab 0 {name}.oct", stdin=os.path.join(d, "pt.pts"), cwd=d).split()[0]))
print(f"1. Glass: Radiance transmissivity {tn:.4f} (converted from VT {s.GLAZING_VT}); "
      f"measured normal-incidence transmittance {vals[0] / vals[1]:.4f}")

# 2. convergence -----------------------------------------------------------------
d = os.path.join(work, "convergence")
os.makedirs(d, exist_ok=True)
os.system(f"cp {os.path.join(src, 'scene.rad')} {d}/")
print("2. Convergence, DF at 1.5 m:")
for params in ["-ab 6 -ad 65536 -lw 1.5e-5", "-ab 8 -ad 65536 -lw 1.5e-5", "-ab 10 -ad 131072 -lw 5e-6", "-ab 12 -ad 131072 -lw 2e-6"]:
    print(f"   {params:30s} {df_at(d, [1.5], params)[0]:.3f} %")

# 3. window variants --------------------------------------------------------------
variants = {
    "as drawn in Fig. 5(a), 6 panes (4.58 m2)": s.WINDOW_PANES,
    "no frames: two full-width bands (5.18 m2)": [(0.0, 3.05, 0.82, 1.91), (0.0, 3.05, 2.01, 2.62)],
    "one frameless pane, sill to ceiling (5.86 m2)": [(0.0, 3.05, 0.82, 2.74)],
}
print("3. Window variants (explanation only):")
original = s.WINDOW_PANES
for i, (name, panes) in enumerate(variants.items()):
    s.WINDOW_PANES = panes
    model, _ = s.build_model()
    geo, mods = model_to_rad(model)
    d = os.path.join(work, f"variant{i}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "scene.rad"), "w") as f:
        f.write(mods + "\n" + geo)
    df = df_at(d, [1.5, 4.5], s.RAD_PARAMS_DC)
    print(f"   {name:46s} DF 1.5 m {df[0]:.2f} %, 4.5 m {df[1]:.2f} %")
s.WINDOW_PANES = original
