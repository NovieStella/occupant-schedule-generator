# Case study: Reinhart reference office, Malmö

Final run of 2026-10-20 with the Occupant Schedule Generator v1.0.

**Input:** `../daylight/output/illuminance_4.5m.csv`. This is simulated with Radiance for the Reinhart (2004) office (see `../daylight/README.md`). The sensor sits on the centre line, 0.8 m high and 4.5 m from the window. Daylit mean 697 lx, daylight factor 1.4 %.

**Settings:**
- 100 occupants, seed 12345.
- μ (hourly) = 0.38, 0.67 and 0.93.
- 50 % Dd users.
- Sveby presence profile, weekends absent.
- 1 January is a Wednesday, EU summer time applied to office hours.
- Setpoint 500 lx, LPD 10 W/m² (4 W/m² as a sensitivity), floor area 18.6 m² (Reinhart's 3.05 × 6.1 m room; the per-m² results do not depend on it).

## Result (μ = 0.38, kWh/m²·yr)
| | Fixed (Sveby) | Daylight effect | Presence effect | Behaviour effect | Stochastic |
|---|---|---|---|---|---|
| Dd users | 23.5 | −14.8 | −2.6 | +0.1 | **6.1** (P10–P90 5.5–6.9) |
| Di users | 23.5 | −14.8 | −2.7 | +12.2 | **18.2** (P10–P90 17.4–19.1) |

The deterministic case (full occupancy, below 500 lx) uses 8.7 kWh/m²·yr. Ideal switching on each occupant's own presence uses 6.0.

**Finding:** at a realistic desk, occupants who use daylight behave close to ideal switching. About 99 % of the behaviour effect comes from occupants who ignore daylight.

For Dd users, "close to ideal" is a net result of two opposite effects:
- **More energy:** lights left on through some absences, and never switched off while present.
- **Less energy:** dim hours tolerated without switching on.

At μ = 0.67 and 0.93 the second effect wins, and Dd users use 5.9 and 5.8 kWh/m²·yr, slightly below ideal. So the Dd/Di share drives the outcome more than the mean does.

**Spread and outliers:** the upper tail is genuine model behaviour, not an error. Lights left on at a departure stay on until the next departure where they are switched off. For an absence of 12 h or more the switch-off probability is 0.990, so about 1 in 100 departures made with the lights on before a night or weekend leaves them on, for up to 63 h over a weekend. 33 of the 100 occupants leave the lights on over at least one weekend in the year. Occupant 35 (Di) has the most hours lit while absent: 354 h, 144 of them on weekends. Occupant 1 (Di, 1 925 lit hours: 1 708 present + 217 absent) is 47th of 50 Di users.

**Plausibility, not validation:** Reinhart's (2004) DdBd user in Toronto used 9.6 kWh/m²·yr at 15 W/m² (Eq. 1). That's about 6.4 at 10 W/m², against 6.1 here, with a different climate, presence pattern and blinds.

## Files
- `summary_cases.csv`, `summary_occupants.csv`, `metadata.json`, `README.txt`: from the tool's export. The metadata includes every coefficient, setting and assumption, plus the input file's CRC-32.
- `results_page_text.txt`: all result tables as shown on the page.
- `waterfall.png`, `histogram.png`, `energy_table.png`, `weekday_lighting_profile.png`: screenshots of the charts.
- The 8760-row schedule CSVs are not stored here. Re-running the tool with the same file and seed reproduces them exactly.
