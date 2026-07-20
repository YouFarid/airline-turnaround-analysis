/*
Carrier deep-dive analysis for PostgreSQL.

Run this after `03_turnaround_model_postgres.sql`.

The goal is to profile each airline from several angles:
- How hard the aircraft are being worked
- How much schedule pressure exists in the turn plan
- How often late inbound flights recover versus propagate
- Which airports and hours create the most carrier-specific risk
*/


-- 1. Carrier operating profile: one row per airline.
WITH aircraft_days AS (
    SELECT
        reporting_airline,
        tail_number,
        flightdate,
        COUNT(*) + 1 AS completed_flight_legs,
        SUM(airtime) / 60.0 AS airborne_hours,
        SUM(turnaround_minutes) / 60.0 AS ground_hours_between_turns,
        SUM(delay_propagated_flag) AS propagated_delay_events
    FROM v_aircraft_turnarounds
    GROUP BY reporting_airline, tail_number, flightdate
),
carrier_turns AS (
    SELECT
        reporting_airline,
        COUNT(*) AS turnarounds,
        COUNT(DISTINCT tail_number) AS aircraft_tracked,
        COUNT(DISTINCT flightdate) AS operating_days,
        AVG(turnaround_minutes) AS avg_turnaround_minutes,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY turnaround_minutes) AS median_turnaround_minutes,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY turnaround_minutes) AS p90_turnaround_minutes,
        AVG(CASE WHEN turnaround_minutes < 35 THEN 1.0 ELSE 0 END) AS critical_turn_rate,
        AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) AS tight_turn_rate,
        AVG(CASE WHEN turnaround_minutes BETWEEN 45 AND 90 THEN 1.0 ELSE 0 END) AS standard_turn_rate,
        AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) AS idle_turn_rate,
        AVG(inbound_arrival_late_flag) AS inbound_late_rate,
        AVG(next_departure_late_flag) AS next_departure_late_rate,
        AVG(delay_propagated_flag) AS delay_propagation_rate,
        AVG(CASE WHEN inbound_arrival_late_flag = 1 AND next_departure_late_flag = 0 THEN 1.0 ELSE 0 END) AS late_arrival_recovery_rate,
        AVG(arrdelay) AS avg_inbound_arrival_delay,
        AVG(next_dep_delay) AS avg_next_departure_delay,
        AVG(schedule_buffer_after_actual_arrival_minutes) AS avg_remaining_schedule_buffer_minutes
    FROM v_aircraft_turnarounds
    GROUP BY reporting_airline
)
SELECT
    c.reporting_airline,
    c.turnarounds,
    c.aircraft_tracked,
    ROUND(c.turnarounds::numeric / NULLIF(c.aircraft_tracked, 0), 2) AS turns_per_aircraft,
    ROUND(AVG(a.completed_flight_legs), 2) AS avg_daily_legs_per_aircraft,
    ROUND(AVG(a.airborne_hours), 2) AS avg_daily_airborne_hours,
    ROUND(AVG(a.ground_hours_between_turns), 2) AS avg_daily_ground_hours_between_turns,
    ROUND(c.avg_turnaround_minutes, 1) AS avg_turnaround_minutes,
    ROUND(c.median_turnaround_minutes::numeric, 1) AS median_turnaround_minutes,
    ROUND(c.p90_turnaround_minutes::numeric, 1) AS p90_turnaround_minutes,
    ROUND(c.critical_turn_rate * 100, 1) AS pct_critical_under_35_min,
    ROUND(c.tight_turn_rate * 100, 1) AS pct_tight_under_45_min,
    ROUND(c.standard_turn_rate * 100, 1) AS pct_standard_45_to_90_min,
    ROUND(c.idle_turn_rate * 100, 1) AS pct_idle_over_180_min,
    ROUND(c.inbound_late_rate * 100, 1) AS inbound_late_rate,
    ROUND(c.next_departure_late_rate * 100, 1) AS next_departure_late_rate,
    ROUND(c.delay_propagation_rate * 100, 1) AS delay_propagation_rate,
    ROUND(c.late_arrival_recovery_rate * 100, 1) AS late_arrival_recovery_rate,
    ROUND(c.avg_inbound_arrival_delay, 1) AS avg_inbound_arrival_delay,
    ROUND(c.avg_next_departure_delay, 1) AS avg_next_departure_delay,
    ROUND(c.avg_remaining_schedule_buffer_minutes, 1) AS avg_remaining_schedule_buffer_minutes
FROM carrier_turns c
JOIN aircraft_days a
  ON c.reporting_airline = a.reporting_airline
GROUP BY
    c.reporting_airline,
    c.turnarounds,
    c.aircraft_tracked,
    c.avg_turnaround_minutes,
    c.median_turnaround_minutes,
    c.p90_turnaround_minutes,
    c.critical_turn_rate,
    c.tight_turn_rate,
    c.standard_turn_rate,
    c.idle_turn_rate,
    c.inbound_late_rate,
    c.next_departure_late_rate,
    c.delay_propagation_rate,
    c.late_arrival_recovery_rate,
    c.avg_inbound_arrival_delay,
    c.avg_next_departure_delay,
    c.avg_remaining_schedule_buffer_minutes
ORDER BY delay_propagation_rate DESC;


-- 2. Carrier risk matrix: separates schedule pressure from delay propagation.
SELECT
    reporting_airline,
    COUNT(*) AS turnarounds,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS tight_turn_rate,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate,
    ROUND(AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) * 100, 1) AS idle_turn_rate,
    CASE
        WHEN AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) >= 0.25
         AND AVG(delay_propagated_flag) >= 0.15
        THEN 'High pressure / high propagation'
        WHEN AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) >= 0.25
        THEN 'High pressure / mostly recovering'
        WHEN AVG(delay_propagated_flag) >= 0.15
        THEN 'Propagation risk without tight turns'
        WHEN AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) >= 0.08
        THEN 'Idle-time heavy'
        ELSE 'Balanced'
    END AS carrier_risk_segment
FROM v_aircraft_turnarounds
GROUP BY reporting_airline
ORDER BY delay_propagation_rate DESC;


-- 3. Carrier by airport: where each airline's turnarounds struggle most.
SELECT
    reporting_airline,
    dest AS turnaround_airport,
    destcityname AS airport_city,
    COUNT(*) AS turnarounds,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS tight_turn_rate,
    ROUND(AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) * 100, 1) AS idle_turn_rate,
    ROUND(AVG(inbound_arrival_late_flag) * 100, 1) AS inbound_late_rate,
    ROUND(AVG(next_departure_late_flag) * 100, 1) AS next_departure_late_rate,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate,
    ROUND(AVG(schedule_buffer_after_actual_arrival_minutes), 1) AS avg_remaining_schedule_buffer_minutes
FROM v_aircraft_turnarounds
GROUP BY reporting_airline, dest, destcityname
HAVING COUNT(*) >= 75
ORDER BY reporting_airline, delay_propagation_rate DESC, turnarounds DESC;


-- 4. Carrier by hour: delay propagation across the operating day.
SELECT
    reporting_airline,
    EXTRACT(HOUR FROM actual_arrival_ts)::integer AS arrival_hour,
    COUNT(*) AS turnarounds,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS tight_turn_rate,
    ROUND(AVG(inbound_arrival_late_flag) * 100, 1) AS inbound_late_rate,
    ROUND(AVG(next_departure_late_flag) * 100, 1) AS next_departure_late_rate,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate
FROM v_aircraft_turnarounds
GROUP BY reporting_airline, arrival_hour
HAVING COUNT(*) >= 50
ORDER BY reporting_airline, arrival_hour;


-- 5. Best recovery airports by airline: late inbound arrives, next flight still leaves on time.
SELECT
    reporting_airline,
    dest AS turnaround_airport,
    destcityname AS airport_city,
    COUNT(*) FILTER (WHERE inbound_arrival_late_flag = 1) AS late_inbound_turns,
    ROUND(
        AVG(CASE WHEN inbound_arrival_late_flag = 1 AND next_departure_late_flag = 0 THEN 1.0 ELSE 0 END)
        FILTER (WHERE inbound_arrival_late_flag = 1) * 100,
        1
    ) AS late_inbound_recovery_rate,
    ROUND(AVG(turnaround_minutes) FILTER (WHERE inbound_arrival_late_flag = 1), 1) AS avg_turnaround_after_late_arrival
FROM v_aircraft_turnarounds
GROUP BY reporting_airline, dest, destcityname
HAVING COUNT(*) FILTER (WHERE inbound_arrival_late_flag = 1) >= 25
ORDER BY reporting_airline, late_inbound_recovery_rate DESC, late_inbound_turns DESC;


-- 6. Route-pair pressure: which inbound-to-outbound rotations create risk.
SELECT
    reporting_airline,
    origin || ' -> ' || dest AS inbound_route,
    next_origin || ' -> ' || next_dest AS outbound_route,
    dest AS turnaround_airport,
    COUNT(*) AS turnarounds,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS tight_turn_rate,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate,
    ROUND(AVG(arrdelay), 1) AS avg_inbound_arrival_delay,
    ROUND(AVG(next_dep_delay), 1) AS avg_next_departure_delay
FROM v_aircraft_turnarounds
GROUP BY reporting_airline, inbound_route, outbound_route, turnaround_airport
HAVING COUNT(*) >= 10
ORDER BY delay_propagation_rate DESC, turnarounds DESC;


-- 7. Tail-number outliers: aircraft-days with heavy utilization or repeated propagation.
SELECT
    reporting_airline,
    tail_number,
    flightdate,
    COUNT(*) + 1 AS completed_flight_legs,
    ROUND(SUM(airtime) / 60.0, 2) AS airborne_hours,
    ROUND(SUM(turnaround_minutes) / 60.0, 2) AS ground_hours_between_turns,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    SUM(CASE WHEN turnaround_minutes < 45 THEN 1 ELSE 0 END) AS tight_turns,
    SUM(delay_propagated_flag) AS propagated_delay_events
FROM v_aircraft_turnarounds
GROUP BY reporting_airline, tail_number, flightdate
HAVING COUNT(*) + 1 >= 4
ORDER BY propagated_delay_events DESC, airborne_hours DESC, completed_flight_legs DESC;
