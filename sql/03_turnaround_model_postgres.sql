/*
Aircraft turnaround model for PostgreSQL.

The raw BTS table is one row per flight. This model turns it into one row per
valid aircraft turn: a flight arrives, the same tail number stays at that
airport, then leaves on its next flight.
*/

DROP VIEW IF EXISTS v_aircraft_turnarounds;
DROP VIEW IF EXISTS v_completed_flights;


CREATE VIEW v_completed_flights AS
WITH cleaned AS (
    SELECT
        year,
        quarter,
        month,
        dayofmonth,
        dayofweek,
        flightdate,
        reporting_airline,
        iata_code_reporting_airline,
        NULLIF(TRIM(tail_number), '') AS tail_number,
        flight_number_reporting_airline,
        origin,
        origincityname,
        originstate,
        dest,
        destcityname,
        deststate,
        crsdeptime,
        deptime,
        depdelay,
        depdelayminutes,
        depdel15,
        taxiout,
        wheelsoff,
        wheelson,
        taxiin,
        crsarrtime,
        arrtime,
        arrdelay,
        arrdelayminutes,
        arrdel15,
        cancelled,
        diverted,
        crselapsedtime,
        actualelapsedtime,
        airtime,
        distance,
        carrierdelay,
        weatherdelay,
        nasdelay,
        securitydelay,
        lateaircraftdelay,

        /*
        BTS clock fields are HHMM strings. The lpad/modulo pattern handles
        values like 5, 45, 930, and 2400 consistently.
        */
        (SUBSTRING(LPAD(((NULLIF(crsdeptime, '')::integer % 2400)::text), 4, '0'), 1, 2)::integer * 60
            + SUBSTRING(LPAD(((NULLIF(crsdeptime, '')::integer % 2400)::text), 4, '0'), 3, 2)::integer) AS sched_dep_min,
        (SUBSTRING(LPAD(((NULLIF(crsarrtime, '')::integer % 2400)::text), 4, '0'), 1, 2)::integer * 60
            + SUBSTRING(LPAD(((NULLIF(crsarrtime, '')::integer % 2400)::text), 4, '0'), 3, 2)::integer) AS sched_arr_min,
        (SUBSTRING(LPAD(((NULLIF(deptime, '')::integer % 2400)::text), 4, '0'), 1, 2)::integer * 60
            + SUBSTRING(LPAD(((NULLIF(deptime, '')::integer % 2400)::text), 4, '0'), 3, 2)::integer) AS actual_dep_min,
        (SUBSTRING(LPAD(((NULLIF(arrtime, '')::integer % 2400)::text), 4, '0'), 1, 2)::integer * 60
            + SUBSTRING(LPAD(((NULLIF(arrtime, '')::integer % 2400)::text), 4, '0'), 3, 2)::integer) AS actual_arr_min
    FROM raw_on_time_performance
    WHERE COALESCE(cancelled, 0) = 0
      AND COALESCE(diverted, 0) = 0
      AND NULLIF(TRIM(tail_number), '') IS NOT NULL
      AND deptime IS NOT NULL
      AND arrtime IS NOT NULL
      AND crsdeptime IS NOT NULL
      AND crsarrtime IS NOT NULL
)
SELECT
    *,
    flightdate::timestamp
        + make_interval(mins => (
            sched_dep_min
            + CASE WHEN crsdeptime = '2400' THEN 1440 ELSE 0 END
        )::integer) AS scheduled_departure_ts,

    flightdate::timestamp
        + make_interval(mins => (
            actual_dep_min
            + CASE
                WHEN deptime = '2400' THEN 1440
                WHEN actual_dep_min + COALESCE(depdelay, 0) < 0 THEN 1440
                ELSE 0
              END
        )::integer) AS actual_departure_ts,

    flightdate::timestamp
        + make_interval(mins => (
            actual_arr_min
            + CASE
                WHEN arrtime = '2400' THEN 1440
                WHEN actual_arr_min < actual_dep_min THEN 1440
                ELSE 0
              END
        )::integer) AS actual_arrival_ts
FROM cleaned;


CREATE VIEW v_aircraft_turnarounds AS
WITH sequenced AS (
    SELECT
        f.*,
        LEAD(flightdate) OVER aircraft_day AS next_flight_date,
        LEAD(reporting_airline) OVER aircraft_day AS next_airline,
        LEAD(flight_number_reporting_airline) OVER aircraft_day AS next_flight_number,
        LEAD(origin) OVER aircraft_day AS next_origin,
        LEAD(origincityname) OVER aircraft_day AS next_origin_city,
        LEAD(dest) OVER aircraft_day AS next_dest,
        LEAD(crsdeptime) OVER aircraft_day AS next_crs_dep_time,
        LEAD(deptime) OVER aircraft_day AS next_dep_time,
        LEAD(depdelay) OVER aircraft_day AS next_dep_delay,
        LEAD(depdel15) OVER aircraft_day AS next_dep_del15,
        LEAD(actual_departure_ts) OVER aircraft_day AS next_actual_departure_ts,
        LEAD(scheduled_departure_ts) OVER aircraft_day AS next_scheduled_departure_ts
    FROM v_completed_flights f
    WINDOW aircraft_day AS (
        PARTITION BY tail_number, flightdate
        ORDER BY scheduled_departure_ts, actual_departure_ts, flight_number_reporting_airline
    )
),
turns AS (
    SELECT
        *,
        ROUND((EXTRACT(EPOCH FROM (next_actual_departure_ts - actual_arrival_ts)) / 60.0)::numeric, 1) AS turnaround_minutes,
        ROUND((EXTRACT(EPOCH FROM (next_scheduled_departure_ts - actual_arrival_ts)) / 60.0)::numeric, 1) AS schedule_buffer_after_actual_arrival_minutes
    FROM sequenced
    WHERE next_actual_departure_ts IS NOT NULL
      AND dest = next_origin
)
SELECT
    tail_number,
    flightdate,
    reporting_airline,
    flight_number_reporting_airline,
    origin,
    origincityname,
    originstate,
    dest,
    destcityname,
    deststate,
    crsdeptime,
    deptime,
    depdelay,
    depdel15,
    taxiout,
    wheelsoff,
    wheelson,
    taxiin,
    crsarrtime,
    arrtime,
    arrdelay,
    arrdel15,
    crselapsedtime,
    actualelapsedtime,
    airtime,
    distance,
    carrierdelay,
    weatherdelay,
    nasdelay,
    securitydelay,
    lateaircraftdelay,
    actual_departure_ts,
    actual_arrival_ts,

    next_flight_date,
    next_airline,
    next_flight_number,
    next_origin,
    next_origin_city,
    next_dest,
    next_crs_dep_time,
    next_dep_time,
    next_dep_delay,
    next_dep_del15,
    next_scheduled_departure_ts,
    next_actual_departure_ts,

    turnaround_minutes,
    schedule_buffer_after_actual_arrival_minutes,
    CASE WHEN COALESCE(arrdelay, 0) >= 15 THEN 1 ELSE 0 END AS inbound_arrival_late_flag,
    CASE WHEN COALESCE(next_dep_delay, 0) >= 15 THEN 1 ELSE 0 END AS next_departure_late_flag,
    CASE
        WHEN COALESCE(arrdelay, 0) >= 15
         AND COALESCE(next_dep_delay, 0) >= 15
        THEN 1
        ELSE 0
    END AS delay_propagated_flag,
    CASE
        WHEN turnaround_minutes < 0 THEN 'Invalid sequence'
        WHEN turnaround_minutes < 35 THEN 'Critical: under 35 min'
        WHEN turnaround_minutes < 45 THEN 'Tight: 35-44 min'
        WHEN turnaround_minutes <= 90 THEN 'Standard: 45-90 min'
        WHEN turnaround_minutes <= 180 THEN 'Long: 91-180 min'
        ELSE 'Idle: over 180 min'
    END AS turnaround_category
FROM turns
WHERE turnaround_minutes BETWEEN 0 AND 720;
