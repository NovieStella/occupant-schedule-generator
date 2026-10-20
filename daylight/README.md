# Case-study daylight input

Annual hourly work-plane illuminance for the Reinhart (2004) reference office in Malmö, simulated with honeybee-radiance and Radiance 6.0a. The full model set-up is in `output/daylight_metadata.json`.

## Reproduce
```
pip install pyradiance honeybee-radiance      # pyradiance ships the Radiance binaries
python3 simulate_reinhart_office.py SWE_SN_Malmo.026350_TMYx.epw output
```
It takes about 2 minutes on 2 cores. Add `--no-rtrace` to skip the slower independent daylight-factor check. The EPW is not in the repo; it comes from climate.onebuilding.org (Malmö TMYx).

## Model
- **Room:** 3.05 m wide × 6.1 m deep × 2.74 m high, facade due south, no obstructions, ground albedo 20 %. Reflectances: ceiling 80 %, walls 50 %, floor 20 %. Double low-e glazing, VT 72 %. No blinds.
- **Window:** six panes digitised from Fig. 5(a), 4.58 m² of glazing (55 % of the facade).
- **Sensors:** room centre line, 0.8 m high, every 0.5 m from the window.
- **Method:** two-phase daylight coefficients with an exact direct-sun component, the same method as the Ladybug Tools annual-daylight recipe. Perez sky, Tregenza patches, `-ab 6 -ad 65536 -lw 1.5e-5`.
- **Time:** standard time (UTC+1), row 1 = 1 January 00:00–01:00.

## Checks (2026-10-20)
| Depth (m) | 0.5 | 1.0 | **1.5** | 2.0 | 2.5 | 3.0 | 3.5 | 4.0 | **4.5** | 5.0 | 5.5 | 6.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DF, daylight coefficients (%) | 19.7 | 13.1 | **8.5** | 5.7 | 3.9 | 2.9 | 2.2 | 1.7 | **1.4** | 1.2 | 1.0 | 1.1 |
| DF, rtrace check (%) | 19.6 | 13.2 | **8.5** | 5.8 | 4.0 | 2.9 | 2.1 | 1.7 | **1.3** | 1.1 | 1.0 | 1.0 |
| Daylit mean (lx) | 9 794 | 7 447 | 4 400 | 2 807 | 2 068 | 1 469 | 1 123 | 870 | **697** | 556 | 492 | 544 |

1. **Daylight factor at 1.5 m: 8.5 %, against 11 % in Reinhart (2004).** The two independent methods agree, so the gap comes from the model, not the numerics. Removing all frames gives 9.6 %. Only one frameless pane from the sill to the ceiling reaches 10.9 %, and that contradicts Fig. 5(a). The geometry is therefore kept as drawn, and the gap is reported.
2. **Timing check:** passes at every sensor. The peak falls in the 12:00 interval and there is no light at night.
3. **Falls with depth:** yes, from 0.5 to 5.5 m. At 6.0 m (0.1 m from the back wall) values rise slightly, because low winter sun reaches the back of the room and the back wall reflects light.

**Case-study input:** `output/illuminance_4.5m.csv`, 8760 rows plus a header. Daylit mean 697 lx over 4 598 h; 64 % of 08:00–17:00 hours are at or above 500 lx.
