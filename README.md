# Occupant Schedule Generator

A single-page browser tool that turns annual work-plane illuminance into stochastic occupant lighting schedules, using published, cited behaviour models (Page et al. 2008; Reinhart 2004, Lightswitch-2002; Hunt 1979). It compares the spread of lighting energy use with a fixed standard (Sveby) schedule.

**Status:** version 1.0 (milestones 1–7 of 8). Case study of the Reinhart (2004) reference office in Malmö in `case-study/`; the method note is on the page. EnergyPlus import tested. Next: milestone 8, the Honeybee case-study run (waiting for a Rhino licence).

## Use
Open `index.html` in a browser (or the GitHub Pages link) and load a CSV with one column of 8760 hourly illuminance values in lux. The file is read locally; nothing is uploaded.

Open `index.html?test` to run the built-in known-answer tests.

## Compatibility of the exported schedules
| Program | Status |
|---|---|
| EnergyPlus (`Schedule:File`) | **Tested** with EnergyPlus 25.2.0: values, hours and weekdays read exactly, with and without daylight saving in the model (`Adjust Schedule for Daylight Savings = No`). See `energyplus-test/`. |
| Honeybee | Expected to work, because Honeybee writes the same `Schedule:File` objects for EnergyPlus. Not yet tested. |
| IES VE (free-form profiles) | Expected to work, not yet tested. |
| IDA ICE | Expected to work, not yet tested. |

## Files
- `index.html` — the whole tool (HTML, CSS, vanilla JS; Chart.js from cdnjs)
- `PROJECT_SPEC.md` — scope, models, milestones
- `CLAUDE.md` — working rules for building it with Claude
- `test-data/` — synthetic CSVs for testing the upload (not real daylight data)
- `daylight/` — Radiance simulation of the case-study office and its illuminance output
- `case-study/` — final case-study results, summaries and charts
- `energyplus-test/` — EnergyPlus Schedule:File import test (passed)
