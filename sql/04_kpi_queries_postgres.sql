/*
PostgreSQL KPI and worksheet queries.

Run these after creating v_aircraft_turnarounds. Each query maps directly to a
Tableau worksheet or an interview-ready analysis table.
*/


-- Executive monthly scorecard.
SELECT
    COUNT(*) AS turnarounds_analyzed,
    COUNT(DISTINCT tail_number) AS aircraft_tracked,
    COUNT(DISTINCT reporting_airline) AS carriers_analyzed,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_tight_turnarounds,
    ROUND(AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_idle_turnarounds,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS pct_delay_propagated,
    ROUND(AVG(airtime) / 60.0, 2) AS avg_inbound_air_hours
FROM v_aircraft_turnarounds;


-- Carrier efficiency ranking.
SELECT
    reporting_airline,
    COUNT(*) AS turnarounds,
    COUNT(DISTINCT tail_number) AS aircraft,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT tail_number), 2) AS turnarounds_per_aircraft,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_under_45_min,
    ROUND(AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_over_180_min,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate
FROM v_aircraft_turnarounds
GROUP BY reporting_airline
HAVING COUNT(*) >= 100
ORDER BY delay_propagation_rate DESC, avg_turnaround_minutes DESC;


-- Airport bottlenecks. Destination is the turnaround airport.
SELECT
    dest AS turnaround_airport,
    destcityname AS airport_city,
    COUNT(*) AS turnarounds,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_under_45_min,
    ROUND(AVG(CASE WHEN turnaround_minutes > 180 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_over_180_min,
    ROUND(AVG(inbound_arrival_late_flag) * 100, 1) AS inbound_late_rate,
    ROUND(AVG(next_departure_late_flag) * 100, 1) AS next_departure_late_rate,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate
FROM v_aircraft_turnarounds
GROUP BY dest, destcityname
HAVING COUNT(*) >= 250
ORDER BY delay_propagation_rate DESC, turnarounds DESC;


-- Time-of-day heatmap.
SELECT
    reporting_airline,
    SUBSTRING(LPAD(crsarrtime, 4, '0'), 1, 2)::integer AS arrival_hour,
    COUNT(*) AS turnarounds,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    ROUND(AVG(CASE WHEN turnaround_minutes < 45 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_under_45_min,
    ROUND(AVG(delay_propagated_flag) * 100, 1) AS delay_propagation_rate
FROM v_aircraft_turnarounds
GROUP BY reporting_airline, arrival_hour
HAVING COUNT(*) >= 50
ORDER BY reporting_airline, arrival_hour;


-- Aircraft utilization proxy by tail number and day.
SELECT
    tail_number,
    flightdate,
    reporting_airline,
    COUNT(*) + 1 AS completed_flight_legs,
    ROUND(SUM(airtime) / 60.0, 2) AS airborne_hours,
    ROUND(SUM(turnaround_minutes) / 60.0, 2) AS ground_hours_between_turns,
    ROUND(AVG(turnaround_minutes), 1) AS avg_turnaround_minutes,
    SUM(delay_propagated_flag) AS propagated_delay_events
FROM v_aircraft_turnarounds
GROUP BY tail_number, flightdate, reporting_airline
HAVING COUNT(*) + 1 >= 3
ORDER BY airborne_hours DESC, completed_flight_legs DESC;


-- Tail-number sequence for Tableau Gantt/timeline views.
SELECT
    tail_number,
    flightdate,
    reporting_airline,
    flight_number_reporting_airline,
    origin || ' -> ' || dest AS route,
    actual_departure_ts,
    actual_arrival_ts,
    ROUND(actualelapsedtime, 1) AS block_minutes,
    arrdelay,
    next_flight_number,
    next_origin || ' -> ' || next_dest AS next_route,
    next_actual_departure_ts,
    turnaround_minutes,
    turnaround_category,
    delay_propagated_flag
FROM v_aircraft_turnarounds
ORDER BY tail_number, flightdate, actual_departure_ts;
