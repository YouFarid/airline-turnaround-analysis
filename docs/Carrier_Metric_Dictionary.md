# Carrier Metric Dictionary

Use these explanations in your README, Tableau captions, or interview notes.

## Turnarounds

Number of valid same-aircraft ground turns reconstructed from the BTS data.

Why it matters:

Higher volume makes the metric more reliable and shows the airline has a larger operational footprint in the sample.

## Aircraft Tracked

Number of distinct tail numbers included in the carrier's rotations.

Why it matters:

This gives context for fleet scale in the dataset. It also supports utilization-style metrics like turns per aircraft.

## Turns Per Aircraft

Turnarounds divided by distinct aircraft.

Why it matters:

This is a simple utilization proxy. More turns per aircraft can indicate higher aircraft productivity, but it can also create more recovery pressure if schedule buffers are too tight.

## Average Daily Legs Per Aircraft

Average number of completed flight legs per aircraft-day.

Why it matters:

This shows how intensely aircraft are scheduled. It is useful because two carriers may have similar delay rates but very different operating models.

## Average Daily Airborne Hours

Average hours each aircraft spends flying per day.

Why it matters:

Aircraft generate revenue while flying. This metric helps compare utilization beyond simple flight count.

## Average Turnaround Minutes

Average ground time between an aircraft's arrival and next departure.

Why it matters:

Shorter turns can improve utilization, but they reduce recovery buffer. Longer turns can protect reliability but may indicate inefficient aircraft use.

## Median Turnaround Minutes

Middle value of turnaround time.

Why it matters:

The median is less distorted by long idle periods and often better represents the typical turn.

## P90 Turnaround Minutes

The 90th percentile turnaround time.

Why it matters:

This shows the long-ground-time tail. A high P90 means many aircraft sit significantly longer than the typical turn.

## Critical Turn Rate

Percent of turns under 35 minutes.

Why it matters:

These are high-pressure turns where a small inbound delay can easily affect the next departure.

## Tight Turn Rate

Percent of turns under 45 minutes.

Why it matters:

This measures schedule pressure. High tight-turn rate is not automatically bad, but it should be compared against delay propagation.

## Idle Turn Rate

Percent of turns over 180 minutes.

Why it matters:

This can indicate low utilization, overnight-like gaps, positioning, or deliberate schedule buffers.

## Inbound Late Rate

Percent of turns where the arriving flight was at least 15 minutes late.

Why it matters:

This is the amount of disruption entering the ground operation.

## Next Departure Late Rate

Percent of turns where the next flight left at least 15 minutes late.

Why it matters:

This is the operational outcome after the turn.

## Delay Propagation Rate

Percent of turns where the inbound flight arrived 15+ minutes late and the next flight also departed 15+ minutes late.

Why it matters:

This is the core reliability metric. It captures when delay carries through the aircraft rotation.

## Late Arrival Recovery Rate

Percent of late inbound turns where the next flight still departed less than 15 minutes late.

Why it matters:

This is the positive version of delay propagation. It identifies airlines or airports that absorb disruption well.

## Remaining Schedule Buffer

Minutes between actual arrival and the next scheduled departure.

Why it matters:

This shows how much planned buffer remained after the aircraft actually arrived. Negative or very low values suggest the next flight was already under pressure before boarding, servicing, and crew processes finished.
