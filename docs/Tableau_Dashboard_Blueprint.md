# Tableau Dashboard Blueprint

Project: **Aircraft Utilization and Turnaround Efficiency Analysis**

Primary Tableau data source:

`outputs/tableau_aircraft_turnarounds_april_2026.csv`

## Dashboard 1: Executive Operations Scorecard

Purpose: Give a recruiter or stakeholder the whole project in 30 seconds.

KPIs:

- Turnarounds analyzed
- Aircraft tracked
- Average turnaround minutes
- Median turnaround minutes
- Percent under 45 minutes
- Percent over 180 minutes
- Delay propagation rate

Recommended visuals:

- KPI tiles across the top
- Bar chart: delay propagation rate by carrier
- Bar chart: average turnaround by carrier
- Donut or stacked bar: turnaround category mix
- Short recommendation panel with 3 operational takeaways

Core filters:

- Reporting airline
- Turnaround airport
- Arrival hour
- Turnaround category

## Dashboard 2: Airport Bottleneck Map

Purpose: Find airports where aircraft turns create the most operational risk.

Visuals:

- Symbol map by `DestCityName` or `Dest`
- Bar chart: top airports by `delay_propagation_rate`
- Bar chart: top airports by `% under 45 minutes`
- Scatterplot:
  - X: average turnaround minutes
  - Y: delay propagation rate
  - Size: turnarounds
  - Color: percent under 45 minutes

Interpretation:

- High propagation plus high tight-turn percentage suggests schedule pressure.
- High propagation plus long average turns may suggest congestion, gate constraints, or carrier-specific disruptions.
- Very long turns can represent aircraft idling, inefficient scheduling, or overnight positioning.

## Dashboard 3: Carrier Efficiency Comparison

Purpose: Compare how airlines use aircraft on the ground.

Visuals:

- Ranking: delay propagation rate by carrier
- Ranking: average turnaround minutes by carrier
- Ranking: turnarounds per aircraft
- Stacked bar: turnaround category mix by carrier
- Box plot: turnaround minutes by carrier

Useful calculated field:

```text
Turnaround Efficiency Segment
IF [Turnaround Minutes] < 45 THEN "Fast/Tight"
ELSEIF [Turnaround Minutes] <= 90 THEN "Standard"
ELSEIF [Turnaround Minutes] <= 180 THEN "Long"
ELSE "Idle"
END
```

## Dashboard 4: Time-of-Day Risk Heatmap

Purpose: Show when operational risk builds throughout the day.

Visuals:

- Heatmap:
  - Columns: arrival hour
  - Rows: reporting airline or turnaround airport
  - Color: delay propagation rate
  - Label: turnarounds
- Line chart: average turnaround minutes by arrival hour
- Line chart: next departure late rate by arrival hour

Interpretation:

- Afternoon/evening spikes often indicate delay accumulation.
- Morning tight turns expose aircraft to risk early in the operating day.

## Dashboard 5: Aircraft Timeline Drilldown

Purpose: This is the technical wow-factor dashboard.

Visuals:

- Tail number selector
- Date selector
- Gantt-style timeline:
  - Flight segment from `actual_departure_ts` to `actual_arrival_ts`
  - Ground segment from `actual_arrival_ts` to `next_actual_departure_ts`
  - Color ground segment by `turnaround_category`
- Tooltip:
  - Current route
  - Next route
  - Arrival delay
  - Next departure delay
  - Turnaround minutes
  - Delay propagated flag

Tableau setup idea:

- Use `actual_departure_ts` as the start time for flight bars.
- Use `ActualElapsedTime` as the flight bar size.
- Use `actual_arrival_ts` as the start time for ground bars.
- Use `turnaround_minutes` as the ground bar size.

## Best Story Points

Use these as captions or talking points:

- Aircraft generate revenue while flying, but schedule reliability depends heavily on how efficiently they turn on the ground.
- The SQL model reconstructs aircraft rotations by sequencing flights with the same tail number.
- The analysis separates normal ground time, tight operational turns, idle time, and propagated delay.
- The dashboard identifies where late arrivals turn into late departures, which is the operational bottleneck airlines care about.

