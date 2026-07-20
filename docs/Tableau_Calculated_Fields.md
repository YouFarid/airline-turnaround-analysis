# Tableau Calculated Fields

Use these calculated fields after connecting to:

`outputs/tableau_aircraft_turnarounds_april_2026.csv`

## Delay Propagation Label

```text
IF [delay_propagated_flag] = 1 THEN "Propagated Delay"
ELSE "No Propagation"
END
```

## Turnaround Risk Level

```text
IF [turnaround_minutes] < 35 THEN "Critical"
ELSEIF [turnaround_minutes] < 45 THEN "Tight"
ELSEIF [turnaround_minutes] <= 90 THEN "Standard"
ELSEIF [turnaround_minutes] <= 180 THEN "Long"
ELSE "Idle"
END
```

## Delay Propagation Rate

```text
AVG([delay_propagated_flag])
```

Format as percentage.

## Tight Turn Rate

```text
AVG(
    IF [turnaround_minutes] < 45 THEN 1 ELSE 0 END
)
```

Format as percentage.

## Idle Turn Rate

```text
AVG(
    IF [turnaround_minutes] > 180 THEN 1 ELSE 0 END
)
```

Format as percentage.

## Next Departure Late Rate

```text
AVG([next_departure_late_flag])
```

Format as percentage.

## Inbound Arrival Late Rate

```text
AVG([inbound_arrival_late_flag])
```

Format as percentage.

## Turnaround Hours

```text
[turnaround_minutes] / 60
```

## Flight Block Hours

```text
[ActualElapsedTime] / 60
```

## Aircraft Rotation

```text
[route] + " | " + [next_route]
```

## Operational Diagnosis

```text
IF [delay_propagated_flag] = 1 AND [turnaround_minutes] < 45 THEN
    "Late inbound + tight turn"
ELSEIF [delay_propagated_flag] = 1 THEN
    "Late inbound carried forward"
ELSEIF [turnaround_minutes] < 45 THEN
    "Tight but recovered"
ELSEIF [turnaround_minutes] > 180 THEN
    "Long ground time"
ELSE
    "Normal turn"
END
```

## Dashboard Color Recommendations

- Critical: red
- Tight: amber
- Standard: blue
- Long: gray
- Idle: dark gray
- Propagated Delay: red
- No Propagation: muted blue/gray

Avoid making every chart the same color. Use color only to encode operational risk.
