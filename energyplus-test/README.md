# EnergyPlus Schedule:File import test

**Result (2026-10-20): passed.** EnergyPlus 25.2.0 reads the exported schedules exactly: same values, same hours, same weekdays.

## What was tested
- **Input:** the case-study export (`occupant-schedules_seed12345_100occ_2026-10-20.zip`), 1 January = Wednesday, EU summer time applied to office hours.
- **Schedules:** 10 `Schedule:File` objects, read with `Rows to Skip at Top = 1`, `Number of Hours of Data = 8760`, `Column Separator = Comma`, `Interpolate to Timestep = No` and `Minutes per Item = 60`, with `Timestep = 4`:
  - lighting and occupancy for occupants 1, 2, 50 and 100
  - the fixed Sveby reference and the deterministic reference
- **Model:** a minimal zone with the case-study size (3.05 × 6.1 m = 18.605 m²) and lights at 10 W/m², using occupant 1's lighting schedule.

| Run | Daylight saving in the IDF | Adjust Schedule for Daylight Savings | Hours differing from the CSV (10 schedules × 8 760 h) |
|---|---|---|---|
| A | none | No | **0** |
| B | last Sunday Mar – last Sunday Oct | No | **0** |
| C | last Sunday Mar – last Sunday Oct | Yes | 68–496 per schedule, all in summer (expected) |

The other checks pass in all three runs:
- **Time alignment:** EnergyPlus hour ending 01:00 on 1 January equals CSV data row 1 (00:00–01:00 standard time), for all 8 760 rows.
- **Day types:** EnergyPlus day types match the export's weekday calendar, with 0 mismatches.
- **Values:** lights energy for occupant 1 is 358.146 kWh/yr in EnergyPlus. That equals the tool's 1 925 lit hours × 10 W/m² × 18.605 m² exactly. Occupant 1 is a Di user in the upper part of the normal range: 1 708 h lit while present plus 217 h lit while absent, 47th of 50 Di users (Di range 1 710–2 025 h).
- **Errors:** none severe. The only warning is about missing ground temperatures, which this test model doesn't need.

**Use "Adjust Schedule for Daylight Savings = No".** The files are already in standard time, with summer time built into office hours. Run C shows that "Yes" would shift them a second time.

## Files
- `test_schedule_file.py`: the test. Run `pip install pyenergyplus-lbnl`, then `python3 test_schedule_file.py EXPORT.zip WEATHER.epw`.
- `schedule_file_test_report.json`: the full results.
- `example_schedule_file_dst_on.idf`: run B's input. It's a template for the `Schedule:File` syntax; place the CSVs next to it.

## Not yet tested
- **Honeybee:** waits on a Rhino licence. Honeybee writes the same `Schedule:File` objects for EnergyPlus.
- **IES VE and IDA ICE:** expected to work, but not tested.
