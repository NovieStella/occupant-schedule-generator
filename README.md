# Occupant Schedule Generator

A single-page browser tool that turns annual work-plane illuminance into stochastic occupant lighting schedules, using published, cited behaviour models (Page et al. 2008; Reinhart 2004, Lightswitch-2002). It compares the spread of lighting energy use with a fixed standard (Sveby) schedule.

**Status:** milestone 1 of 8, data input and preview.

## Use
Open `index.html` in a browser (or the GitHub Pages link) and load a CSV with one column of 8760 hourly illuminance values in lux. The file is read locally; nothing is uploaded.

Open `index.html?test` to run the built-in known-answer tests.

## Files
- `index.html` — the whole tool (HTML, CSS, vanilla JS; Chart.js from cdnjs)
- `PROJECT_SPEC.md` — scope, models, milestones
- `CLAUDE.md` — working rules for building it with Claude
- `test-data/` — synthetic CSVs for testing the upload (not real daylight data)
