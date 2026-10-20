Occupant Schedule Generator — exported schedules

FILES
occupancy_mu<μ>.csv   presence 0/1, one column per occupant
lighting_mu<μ>.csv    lighting 0/1, one column per occupant
*_AVERAGE_of_<N>_occupants_*.csv   hourly MEAN of the individual schedules (fraction 0–1). An average, not an individual schedule: for multi-occupant zones only.
reference_fixed_and_deterministic.csv   column 1 fixed Sveby, column 2 deterministic (full occupancy, below setpoint)
summary_cases.csv, summary_occupants.csv   energy and hours per case and per occupant
metadata.json   seed, settings, coefficients with sources, μ-forcing log, assumptions

FORMAT
8760 data rows + 1 header row. Row 2 = 1 January 00:00–01:00, non-leap year.
Comma separator, point decimal, Windows line endings. Columns occ001_<type> …, type Dd or Di.
All rows in standard time (UTC+1), aligned with the illuminance file used to generate them.
EU summer time applied to occupancy: from 30 Mar to 26 Oct office hours are 1 h earlier in standard time (08:00–17:00 clock = 07:00–16:00 standard).

ENERGYPLUS / HONEYBEE (Schedule:File) — tested with EnergyPlus 25.2.0 (values, hours and weekdays read exactly)
  File Name                        lighting_mu<μ>.csv
  Column Number                    occupant number (1 = first occupant)
  Rows to Skip at Top              1
  Number of Hours of Data          8760
  Column Separator                 Comma
  Interpolate to Timestep          No
  Minutes per Item                 60
  Adjust Schedule for Daylight Savings   No   (the files are in standard time; summer time is already in the occupancy)

Honeybee, IES VE and IDA ICE: plain CSV, one column per occupant. Expected to work, not yet tested.

Run: seed 12345, 100 occupants, μ (hourly) 0.38, 0.67, 0.93, 1 January = Wed, setpoint 500 lx, LPD 10 W/m².
