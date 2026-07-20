# Carrier Analysis Tableau Guide

Use this after Tableau is connected to the PostgreSQL view:

`v_aircraft_turnarounds`

This guide builds a comprehensive airline-by-airline operating analysis. The goal is to make each carrier feel like a profile: utilization, schedule pressure, delay propagation, recovery ability, airport exposure, and time-of-day risk.

## Dashboard 1: Carrier Executive Scorecard

Purpose: Compare airlines at a high level.

Worksheets:

1. Turnarounds by carrier
2. Aircraft tracked by carrier
3. Average turnaround minutes
4. Tight turn rate
5. Idle turn rate
6. Delay propagation rate
7. Late arrival recovery rate

Recommended layout:

- KPI row across the top
- Carrier risk scatterplot in the middle
- Turnaround category mix at the bottom

Key calculated fields:

```text
Tight Turn Flag
IF [turnaround_minutes] < 45 THEN 1 ELSE 0 END
```

```text
Idle Turn Flag
IF [turnaround_minutes] > 180 THEN 1 ELSE 0 END
```

```text
Late Arrival Recovery Flag
IF [inbound_arrival_late_flag] = 1 AND [next_departure_late_flag] = 0 THEN 1 ELSE 0 END
```

```text
Late Arrival Recovery Rate
SUM([Late Arrival Recovery Flag]) / SUM([inbound_arrival_late_flag])
```

## Dashboard 2: Carrier Risk Matrix

Purpose: Separate airlines that run tight turns from airlines where delays actually propagate.

Chart type: Scatterplot

Fields:

- Columns: `AVG([Tight Turn Flag])`
- Rows: `AVG([delay_propagated_flag])`
- Detail: `reporting_airline`
- Label: `reporting_airline`
- Size: `COUNT([tail_number])` or `COUNT([turnaround_minutes])`
- Color: `AVG([Idle Turn Flag])`

Format:

- Tight turn rate as percentage
- Delay propagation rate as percentage
- Idle turn rate as percentage

Interpretation:

- Upper right: tight schedules and high propagation risk
- Lower right: tight schedules but strong recovery
- Upper left: delays propagate even without tight turns, likely airport congestion or network disruption
- Lower left: balanced operation

## Dashboard 3: Carrier Turnaround Distribution

Purpose: Show whether average turnaround hides risky tails.

Chart type: Box plot or histogram

Fields:

- Columns: `reporting_airline`
- Rows: `turnaround_minutes`
- Color: `turnaround_category`

Add filter:

- Keep turnaround minutes between 0 and 240 for the first view
- Add an optional filter to include idle turns over 240 minutes

Interpretation:

- A carrier can have a reasonable average but still have many critical turns.
- A wide distribution means less predictable ground operation.

## Dashboard 4: Airport Exposure by Carrier

Purpose: Identify where each airline struggles operationally.

Chart type: Highlight table or bar chart

Fields:

- Rows: `dest`
- Columns: `reporting_airline`
- Color: `AVG([delay_propagated_flag])`
- Label: `COUNT([turnaround_minutes])`

Filters:

- Minimum record count if possible
- Selected carrier
- Arrival hour

Alternative bar chart:

- Filter to one selected carrier
- Rows: `dest`
- Columns: `AVG([delay_propagated_flag])`
- Sort descending
- Size or label: `COUNT([turnaround_minutes])`

Interpretation:

- This is where you turn the analysis into operational recommendations.
- High propagation at high-volume airports deserves the most attention.

## Dashboard 5: Time-of-Day Risk

Purpose: Show when delays start spreading during the operating day.

Chart type: Heatmap

Fields:

- Columns: `arrival_hour`
- Rows: `reporting_airline`
- Color: `AVG([delay_propagated_flag])`
- Label: `COUNT([turnaround_minutes])`

Add a line chart below:

- Columns: `arrival_hour`
- Rows: `AVG([delay_propagated_flag])`
- Color: `reporting_airline`

Interpretation:

- Afternoon and evening spikes often show delay accumulation.
- Morning spikes are more concerning because they can poison the rest of the day.

## Dashboard 6: Recovery Performance

Purpose: Reward airlines/airports that absorb late arrivals without delaying the next flight.

Chart type: Bar chart

Calculated fields:

```text
Late Inbound Count
SUM([inbound_arrival_late_flag])
```

```text
Recovered Late Inbound Count
SUM(
    IF [inbound_arrival_late_flag] = 1
       AND [next_departure_late_flag] = 0
    THEN 1 ELSE 0 END
)
```

```text
Late Inbound Recovery Rate
[Recovered Late Inbound Count] / [Late Inbound Count]
```

Fields:

- Rows: `reporting_airline`
- Columns: `Late Inbound Recovery Rate`
- Label: `Late Inbound Count`
- Color: `Late Inbound Recovery Rate`

Interpretation:

- This is a more sophisticated metric than delay rate because it asks whether the operation recovered from disruption.

## Dashboard 7: Aircraft-Day Drilldown

Purpose: Show concrete examples behind the summary metrics.

Fields:

- Filter: `reporting_airline`
- Filter: `tail_number`
- Filter: `flightdate`
- Rows: `tail_number`
- Columns: `actual_departure_ts`
- Size: `ActualElapsedTime`
- Color: `delay_propagated_flag` or `turnaround_category`

Tooltip:

- Route
- Next route
- Arrival delay
- Next departure delay
- Turnaround minutes
- Delay propagated flag

Interpretation:

- Use this in the portfolio to prove the analysis reconstructed aircraft rotations.

## Best Portfolio Story

Use this structure when presenting:

1. I reconstructed aircraft rotations using tail numbers.
2. I measured whether aircraft ground time was tight, standard, long, or idle.
3. I compared airlines on schedule pressure and delay propagation.
4. I identified airport and time-of-day risk pockets by carrier.
5. I separated bad outcomes from good recovery, which is closer to how airline operations teams think.
