"""
Build the turn-level data used by Tableau and the HTML dashboard.

The BTS file starts as one row per flight. For this project I needed one row
per aircraft turn: a plane arrives at an airport, sits on the ground, then
leaves on its next leg. This script does that matching.
"""

from pathlib import Path
import os

import pandas as pd


DATA_MONTH = "april_2026"
PROJECT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
SUMMARY_DIR = PROJECT_DIR / "data" / "summary"

DEFAULT_SOURCE_CSV = Path(
    r"C:\Users\monae\Downloads\On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_4"
    r"\On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2026_4.csv"
)
SOURCE_CSV = Path(os.environ.get("BTS_CSV_PATH", DEFAULT_SOURCE_CSV))

# Pull only the fields that support this story: aircraft identity, timing,
# route, delay causes, and operating status. The BTS file has a lot more
# columns, but most of them are diversion details that do not help here.
SOURCE_COLUMNS = [
    "Year",
    "Quarter",
    "Month",
    "DayofMonth",
    "DayOfWeek",
    "FlightDate",
    "Reporting_Airline",
    "IATA_CODE_Reporting_Airline",
    "Tail_Number",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "OriginCityName",
    "OriginState",
    "Dest",
    "DestCityName",
    "DestState",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "TaxiOut",
    "WheelsOff",
    "WheelsOn",
    "TaxiIn",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "ArrDelayMinutes",
    "ArrDel15",
    "Cancelled",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "AirTime",
    "Distance",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
]

NUMERIC_COLUMNS = [
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "TaxiOut",
    "TaxiIn",
    "ArrDelay",
    "ArrDelayMinutes",
    "ArrDel15",
    "Cancelled",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "AirTime",
    "Distance",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
]

TABLEAU_FACT_COLUMNS = [
    "Tail_Number",
    "FlightDate",
    "Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "route",
    "Origin",
    "OriginCityName",
    "OriginState",
    "Dest",
    "DestCityName",
    "DestState",
    "actual_departure_ts",
    "actual_arrival_ts",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "DepDel15",
    "TaxiOut",
    "WheelsOff",
    "WheelsOn",
    "TaxiIn",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "ArrDel15",
    "ActualElapsedTime",
    "AirTime",
    "Distance",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
    "next_airline",
    "next_flight_number",
    "next_route",
    "next_origin",
    "next_origin_city",
    "next_dest",
    "next_crs_dep_time",
    "next_dep_time",
    "next_dep_delay",
    "next_dep_del15",
    "next_scheduled_departure_ts",
    "next_actual_departure_ts",
    "turnaround_minutes",
    "schedule_buffer_after_actual_arrival_minutes",
    "turnaround_category",
    "arrival_hour",
    "inbound_arrival_late_flag",
    "next_departure_late_flag",
    "delay_propagated_flag",
]


def clock_to_minutes(values: pd.Series) -> pd.Series:
    """Convert BTS HHMM clock fields to minutes after midnight."""
    numeric = pd.to_numeric(values, errors="coerce")
    hhmm = numeric.mod(2400)
    hours = (hhmm // 100).astype("Int64")
    minutes = (hhmm % 100).astype("Int64")

    # If a weird clock value sneaks in, drop that timestamp instead of letting
    # it scramble an aircraft's flight sequence.
    return (hours * 60 + minutes).mask(minutes >= 60)


def turn_bucket(minutes: float) -> str:
    """Put ground time into labels that make sense on a dashboard."""
    if pd.isna(minutes):
        return "No next flight"
    if minutes < 0:
        return "Invalid sequence"
    if minutes < 35:
        return "Critical: under 35 min"
    if minutes < 45:
        return "Tight: 35-44 min"
    if minutes <= 90:
        return "Standard: 45-90 min"
    if minutes <= 180:
        return "Long: 91-180 min"
    return "Idle: over 180 min"


def load_bts_month() -> pd.DataFrame:
    """Read the monthly BTS CSV."""
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            "Could not find the BTS CSV. Put the file in the default Downloads "
            "location or set BTS_CSV_PATH to the CSV path before running."
        )
    flights = pd.read_csv(SOURCE_CSV, usecols=SOURCE_COLUMNS, low_memory=False)

    for col in NUMERIC_COLUMNS:
        flights[col] = pd.to_numeric(flights[col], errors="coerce")

    flights["FlightDate"] = pd.to_datetime(flights["FlightDate"], errors="coerce")
    flights["Tail_Number"] = flights["Tail_Number"].astype("string").str.strip()
    return flights


def keep_completed_flights(flights: pd.DataFrame) -> pd.DataFrame:
    """Keep flights that have enough information to build a turn."""
    completed = flights[
        (flights["Cancelled"].fillna(0) == 0)
        & (flights["Diverted"].fillna(0) == 0)
        & flights["Tail_Number"].notna()
        & (flights["Tail_Number"] != "")
        & flights["DepTime"].notna()
        & flights["ArrTime"].notna()
    ].copy()

    completed["actual_dep_min"] = clock_to_minutes(completed["DepTime"])
    completed["actual_arr_min"] = clock_to_minutes(completed["ArrTime"])
    completed["sched_dep_min"] = clock_to_minutes(completed["CRSDepTime"])

    completed["actual_departure_ts"] = completed["FlightDate"] + pd.to_timedelta(
        completed["actual_dep_min"], unit="m"
    )
    completed["actual_arrival_ts"] = completed["FlightDate"] + pd.to_timedelta(
        completed["actual_arr_min"], unit="m"
    )

    # If the arrival clock is earlier than the departure clock, the flight
    # crossed midnight.
    crossed_midnight = completed["actual_arr_min"] < completed["actual_dep_min"]
    completed.loc[crossed_midnight, "actual_arrival_ts"] += pd.Timedelta(days=1)

    completed["scheduled_departure_ts"] = completed["FlightDate"] + pd.to_timedelta(
        completed["sched_dep_min"], unit="m"
    )

    return completed.sort_values(
        ["Tail_Number", "FlightDate", "scheduled_departure_ts", "actual_departure_ts"]
    )


def add_next_leg(completed: pd.DataFrame) -> pd.DataFrame:
    """Attach the next same-day flight for each aircraft tail number."""
    next_leg_columns = {
        "Reporting_Airline": "next_airline",
        "Flight_Number_Reporting_Airline": "next_flight_number",
        "Origin": "next_origin",
        "OriginCityName": "next_origin_city",
        "Dest": "next_dest",
        "CRSDepTime": "next_crs_dep_time",
        "DepTime": "next_dep_time",
        "DepDelay": "next_dep_delay",
        "DepDel15": "next_dep_del15",
        "actual_departure_ts": "next_actual_departure_ts",
        "scheduled_departure_ts": "next_scheduled_departure_ts",
    }

    with_next_leg = completed.copy()
    by_aircraft_day = with_next_leg.groupby(["Tail_Number", "FlightDate"])

    for source_col, new_col in next_leg_columns.items():
        with_next_leg[new_col] = by_aircraft_day[source_col].shift(-1)

    return with_next_leg


def build_turnarounds(flights_with_next_leg: pd.DataFrame) -> pd.DataFrame:
    """Create the turn-level table."""
    turns = flights_with_next_leg[
        flights_with_next_leg["next_actual_departure_ts"].notna()
        & (flights_with_next_leg["Dest"] == flights_with_next_leg["next_origin"])
    ].copy()

    turns["turnaround_minutes"] = (
        turns["next_actual_departure_ts"] - turns["actual_arrival_ts"]
    ).dt.total_seconds() / 60

    # Gaps longer than 12 hours are usually overnight rests or scheduling
    # quirks, not the kind of gate turn I am trying to measure here.
    turns = turns[turns["turnaround_minutes"].between(0, 720)].copy()

    turns["schedule_buffer_after_actual_arrival_minutes"] = (
        turns["next_scheduled_departure_ts"] - turns["actual_arrival_ts"]
    ).dt.total_seconds() / 60
    turns["inbound_arrival_late_flag"] = (turns["ArrDelay"].fillna(0) >= 15).astype(int)
    turns["next_departure_late_flag"] = (turns["next_dep_delay"].fillna(0) >= 15).astype(int)
    turns["delay_propagated_flag"] = (
        (turns["inbound_arrival_late_flag"] == 1)
        & (turns["next_departure_late_flag"] == 1)
    ).astype(int)

    turns["turnaround_category"] = turns["turnaround_minutes"].apply(turn_bucket)
    turns["arrival_hour"] = turns["actual_arrival_ts"].dt.hour
    turns["route"] = turns["Origin"] + " -> " + turns["Dest"]
    turns["next_route"] = turns["next_origin"] + " -> " + turns["next_dest"]
    return turns


def summarize_by_carrier(turns: pd.DataFrame) -> pd.DataFrame:
    carrier = (
        turns.groupby("Reporting_Airline")
        .agg(
            turnarounds=("Tail_Number", "size"),
            aircraft=("Tail_Number", "nunique"),
            avg_turnaround_minutes=("turnaround_minutes", "mean"),
            pct_under_45_min=("turnaround_minutes", lambda s: (s < 45).mean() * 100),
            pct_over_180_min=("turnaround_minutes", lambda s: (s > 180).mean() * 100),
            delay_propagation_rate=("delay_propagated_flag", lambda s: s.mean() * 100),
        )
        .reset_index()
    )
    carrier["turnarounds_per_aircraft"] = carrier["turnarounds"] / carrier["aircraft"]
    return carrier.sort_values(
        ["delay_propagation_rate", "avg_turnaround_minutes"], ascending=False
    )


def summarize_by_airport(turns: pd.DataFrame) -> pd.DataFrame:
    airport = (
        turns.groupby(["Dest", "DestCityName"])
        .agg(
            turnarounds=("Tail_Number", "size"),
            avg_turnaround_minutes=("turnaround_minutes", "mean"),
            pct_under_45_min=("turnaround_minutes", lambda s: (s < 45).mean() * 100),
            pct_over_180_min=("turnaround_minutes", lambda s: (s > 180).mean() * 100),
            inbound_late_rate=("inbound_arrival_late_flag", lambda s: s.mean() * 100),
            next_departure_late_rate=("next_departure_late_flag", lambda s: s.mean() * 100),
            delay_propagation_rate=("delay_propagated_flag", lambda s: s.mean() * 100),
        )
        .reset_index()
    )

    # This threshold keeps one-off airport examples from dominating the
    # dashboard while still leaving plenty of regional airports in the analysis.
    return (
        airport.query("turnarounds >= 250")
        .sort_values(["delay_propagation_rate", "turnarounds"], ascending=False)
    )


def build_executive_kpis(
    raw_flights: pd.DataFrame, completed: pd.DataFrame, turns: pd.DataFrame
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "flights_in_raw_file": len(raw_flights),
                "completed_flights_with_tail_number": len(completed),
                "turnarounds_analyzed": len(turns),
                "aircraft_tracked": turns["Tail_Number"].nunique(),
                "carriers_analyzed": turns["Reporting_Airline"].nunique(),
                "avg_turnaround_minutes": turns["turnaround_minutes"].mean(),
                "median_turnaround_minutes": turns["turnaround_minutes"].median(),
                "pct_under_45_min": (turns["turnaround_minutes"] < 45).mean() * 100,
                "pct_over_180_min": (turns["turnaround_minutes"] > 180).mean() * 100,
                "delay_propagation_rate": turns["delay_propagated_flag"].mean() * 100,
            }
        ]
    )


def write_outputs(
    turns: pd.DataFrame,
    carrier_summary: pd.DataFrame,
    airport_summary: pd.DataFrame,
    kpis: pd.DataFrame,
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    turns[TABLEAU_FACT_COLUMNS].to_csv(
        PROCESSED_DIR / f"tableau_aircraft_turnarounds_{DATA_MONTH}.csv", index=False
    )
    carrier_summary.to_csv(
        SUMMARY_DIR / f"carrier_efficiency_summary_{DATA_MONTH}.csv", index=False
    )
    airport_summary.to_csv(
        SUMMARY_DIR / f"airport_bottleneck_summary_{DATA_MONTH}.csv", index=False
    )
    kpis.to_csv(SUMMARY_DIR / f"executive_kpis_{DATA_MONTH}.csv", index=False)


def main() -> None:
    flights = load_bts_month()
    completed = keep_completed_flights(flights)
    turns = build_turnarounds(add_next_leg(completed))

    kpis = build_executive_kpis(flights, completed, turns)
    write_outputs(
        turns=turns,
        carrier_summary=summarize_by_carrier(turns),
        airport_summary=summarize_by_airport(turns),
        kpis=kpis,
    )

    print(kpis.round(2).to_string(index=False))
    print(f"\nWrote turn-level data to {PROCESSED_DIR}")
    print(f"Wrote summary files to {SUMMARY_DIR}")


if __name__ == "__main__":
    main()
