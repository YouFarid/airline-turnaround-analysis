"""
Build the public dashboard.

By this point the data is already at the "aircraft turn" level: one row means
one plane landed, sat on the ground, and left again. This script rolls those
turns into airline, airport, hour, and route summaries, then writes a single
HTML page for GitHub Pages.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
SUMMARY_DIR = PROJECT_DIR / "data" / "summary"
SOURCE_FILE = PROCESSED_DIR / "tableau_aircraft_turnarounds_april_2026.csv"

AIRLINE_NAMES = {
    "AA": "American Airlines",
    "AS": "Alaska Airlines",
    "B6": "JetBlue Airways",
    "DL": "Delta Air Lines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines",
    "MQ": "Envoy Air",
    "NK": "Spirit Airlines",
    "OH": "PSA Airlines",
    "OO": "SkyWest Airlines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "YX": "Republic Airways",
}

COLORS = {
    "navy": "#18324f",
    "blue": "#2f80ed",
    "teal": "#00897b",
    "amber": "#f2a900",
    "red": "#d64545",
    "gray": "#667085",
    "pale": "#eef2f7",
    "ink": "#1f2937",
}


def rate(flags: pd.Series) -> float:
    """Turn a 0/1 column into a percent."""
    return float(flags.mean() * 100) if len(flags) else 0.0


def carrier_label(code: str) -> str:
    return f"{AIRLINE_NAMES.get(code, code)} ({code})"


def load_turns() -> pd.DataFrame:
    """Load the turn-level file built by build_tableau_outputs.py."""
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Missing {SOURCE_FILE}. Run scripts/build_tableau_outputs.py first."
        )
    fields = [
        "Tail_Number",
        "FlightDate",
        "Reporting_Airline",
        "route",
        "Dest",
        "DestCityName",
        "actual_arrival_ts",
        "ArrDelay",
        "AirTime",
        "next_route",
        "next_dep_delay",
        "turnaround_minutes",
        "turnaround_category",
        "arrival_hour",
        "inbound_arrival_late_flag",
        "next_departure_late_flag",
        "delay_propagated_flag",
    ]
    turns = pd.read_csv(SOURCE_FILE, usecols=fields, parse_dates=["FlightDate", "actual_arrival_ts"])
    turns["airline_name"] = turns["Reporting_Airline"].map(AIRLINE_NAMES).fillna(turns["Reporting_Airline"])
    turns["airline"] = turns["Reporting_Airline"].map(carrier_label)

    # I kept these buckets simple because the dashboard is for people who may
    # not know airline operations. "Under 45 minutes" is easier to talk about
    # than a complicated score.
    turns["critical_turn_flag"] = (turns["turnaround_minutes"] < 35).astype(int)
    turns["tight_turn_flag"] = (turns["turnaround_minutes"] < 45).astype(int)
    turns["standard_turn_flag"] = turns["turnaround_minutes"].between(45, 90, inclusive="both").astype(int)
    turns["idle_turn_flag"] = (turns["turnaround_minutes"] > 180).astype(int)
    turns["late_recovery_flag"] = (
        (turns["inbound_arrival_late_flag"] == 1)
        & (turns["next_departure_late_flag"] == 0)
    ).astype(int)
    return turns


def build_carrier_summary(turns: pd.DataFrame) -> pd.DataFrame:
    """Make one scorecard row per airline."""
    aircraft_days = (
        turns.groupby(["airline", "Tail_Number", "FlightDate"])
        .agg(
            completed_flight_legs=("Tail_Number", "size"),
            airborne_hours=("AirTime", lambda s: s.sum() / 60),
            ground_hours=("turnaround_minutes", lambda s: s.sum() / 60),
            propagated_delay_events=("delay_propagated_flag", "sum"),
        )
        .reset_index()
    )
    aircraft_days["completed_flight_legs"] += 1

    carrier = (
        turns.groupby("airline")
        .agg(
            turnarounds=("Tail_Number", "size"),
            aircraft_tracked=("Tail_Number", "nunique"),
            avg_turnaround_minutes=("turnaround_minutes", "mean"),
            median_turnaround_minutes=("turnaround_minutes", "median"),
            p90_turnaround_minutes=("turnaround_minutes", lambda s: s.quantile(0.90)),
            critical_turn_rate=("critical_turn_flag", rate),
            tight_turn_rate=("tight_turn_flag", rate),
            standard_turn_rate=("standard_turn_flag", rate),
            idle_turn_rate=("idle_turn_flag", rate),
            inbound_late_rate=("inbound_arrival_late_flag", rate),
            next_departure_late_rate=("next_departure_late_flag", rate),
            delay_propagation_rate=("delay_propagated_flag", rate),
            late_recovery_rate=("late_recovery_flag", rate),
            avg_arrival_delay=("ArrDelay", "mean"),
            avg_next_departure_delay=("next_dep_delay", "mean"),
        )
        .reset_index()
    )
    daily = (
        aircraft_days.groupby("airline")
        .agg(
            avg_daily_legs_per_aircraft=("completed_flight_legs", "mean"),
            avg_daily_airborne_hours=("airborne_hours", "mean"),
            avg_daily_ground_hours=("ground_hours", "mean"),
        )
        .reset_index()
    )
    carrier = carrier.merge(daily, on="airline", how="left")
    carrier["turns_per_aircraft"] = carrier["turnarounds"] / carrier["aircraft_tracked"]
    carrier["reliability_gap"] = carrier["next_departure_late_rate"] - carrier["inbound_late_rate"]
    return carrier.sort_values("delay_propagation_rate", ascending=False)


def build_airport_summary(turns: pd.DataFrame) -> pd.DataFrame:
    return (
        turns.groupby(["airline", "Dest", "DestCityName"])
        .agg(
            turnarounds=("Tail_Number", "size"),
            avg_turnaround_minutes=("turnaround_minutes", "mean"),
            tight_turn_rate=("tight_turn_flag", rate),
            idle_turn_rate=("idle_turn_flag", rate),
            inbound_late_rate=("inbound_arrival_late_flag", rate),
            delay_propagation_rate=("delay_propagated_flag", rate),
        )
        .reset_index()
        .query("turnarounds >= 75")
        .sort_values(["delay_propagation_rate", "turnarounds"], ascending=False)
    )


def build_hourly_summary(turns: pd.DataFrame) -> pd.DataFrame:
    return (
        turns.groupby(["airline", "arrival_hour"])
        .agg(
            turnarounds=("Tail_Number", "size"),
            avg_turnaround_minutes=("turnaround_minutes", "mean"),
            tight_turn_rate=("tight_turn_flag", rate),
            delay_propagation_rate=("delay_propagated_flag", rate),
        )
        .reset_index()
        .query("turnarounds >= 50")
    )


def build_route_summary(turns: pd.DataFrame) -> pd.DataFrame:
    routes = (
        turns.groupby(["airline", "route", "next_route", "Dest"])
        .agg(
            turnarounds=("Tail_Number", "size"),
            avg_turnaround_minutes=("turnaround_minutes", "mean"),
            tight_turn_rate=("tight_turn_flag", rate),
            delay_propagation_rate=("delay_propagated_flag", rate),
            avg_arrival_delay=("ArrDelay", "mean"),
            avg_next_departure_delay=("next_dep_delay", "mean"),
        )
        .reset_index()
    )
    return routes.query("turnarounds >= 10").sort_values("delay_propagation_rate", ascending=False)


def metric_card(title: str, value: str, help_text: str) -> str:
    return (
        "<div class='kpi'>"
        f"<span>{escape(title)}</span>"
        f"<strong>{escape(value)}</strong>"
        f"<p>{escape(help_text)}</p>"
        "</div>"
    )


def bar_svg(df: pd.DataFrame, label: str, value: str, title: str, explanation: str, suffix: str = "%") -> str:
    data = df.nlargest(13, value)
    width, row_h, left, right = 850, 38, 270, 92
    height = 86 + len(data) * row_h
    max_value = max(float(data[value].max()), 1.0)
    color = COLORS["red"] if "propagation" in value or "late" in value else COLORS["blue"]

    parts = [f"<h3>{escape(title)}</h3><p class='chart-note'>{escape(explanation)}</p>"]
    parts.append(f"<svg viewBox='0 0 {width} {height}' role='img'>")
    for i, row in enumerate(data.itertuples(index=False)):
        y = 54 + i * row_h
        name = str(getattr(row, label))
        val = float(getattr(row, value))
        bar_width = (width - left - right) * val / max_value
        parts.append(f"<text x='8' y='{y + 17}' class='bar-label'>{escape(name)}</text>")
        parts.append(f"<rect x='{left}' y='{y}' width='{bar_width:.1f}' height='24' rx='3' fill='{color}'></rect>")
        parts.append(f"<text x='{left + bar_width + 8:.1f}' y='{y + 17}' class='bar-value'>{val:.1f}{suffix}</text>")
    parts.append("</svg>")
    return "\n".join(parts)


def scatter_svg(df: pd.DataFrame) -> str:
    width, height = 850, 500
    left, right, top, bottom = 78, 36, 40, 64
    x_max = max(df["tight_turn_rate"].max() * 1.08, 30)
    y_max = max(df["delay_propagation_rate"].max() * 1.12, 20)
    volume_max = max(df["turnarounds"].max(), 1)

    parts = [
        "<h3>Airline Risk Map</h3>",
        "<p class='chart-note'>Right means the airline uses more short ground turns. Higher means late arrivals more often make the next flight late too. Bigger circles mean more turnarounds in the data.</p>",
        f"<svg viewBox='0 0 {width} {height}' role='img'>",
        f"<line x1='{left}' y1='{height-bottom}' x2='{width-right}' y2='{height-bottom}' class='axis'/>",
        f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height-bottom}' class='axis'/>",
        f"<text x='{width/2-110}' y='{height-18}' class='axis-title'>Short-turn pressure: % under 45 minutes</text>",
        f"<text x='12' y='{top+10}' class='axis-title'>Delay spread: late arrival + late next departure</text>",
    ]
    for row in df.itertuples(index=False):
        x = left + (float(row.tight_turn_rate) / x_max) * (width - left - right)
        y = (height - bottom) - (float(row.delay_propagation_rate) / y_max) * (height - top - bottom)
        radius = 7 + 16 * (float(row.turnarounds) / volume_max) ** 0.5
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{radius:.1f}' fill='{COLORS['teal']}' opacity='0.74'></circle>")
        parts.append(f"<text x='{x + radius + 4:.1f}' y='{y + 4:.1f}' class='point-label'>{escape(row.airline)}</text>")
    parts.append("</svg>")
    return "\n".join(parts)


def turnaround_mix_svg(turns: pd.DataFrame) -> str:
    order = ["Critical: under 35 min", "Tight: 35-44 min", "Standard: 45-90 min", "Long: 91-180 min", "Idle: over 180 min"]
    palette = {
        "Critical: under 35 min": COLORS["red"],
        "Tight: 35-44 min": COLORS["amber"],
        "Standard: 45-90 min": COLORS["blue"],
        "Long: 91-180 min": COLORS["gray"],
        "Idle: over 180 min": COLORS["ink"],
    }
    mix = pd.crosstab(turns["airline"], turns["turnaround_category"], normalize="index") * 100
    mix = mix.reindex(columns=order, fill_value=0).reset_index()
    width, row_h, left = 920, 34, 230
    height = 92 + len(mix) * row_h
    parts = [
        "<h3>Ground Time Mix</h3>",
        "<p class='chart-note'>Each bar is one airline's ground time. Red and amber are short, high-pressure turns. Dark gray is long idle time.</p>",
        f"<svg viewBox='0 0 {width} {height}' role='img'>",
    ]
    x = left
    for category in order:
        parts.append(f"<rect x='{x}' y='16' width='12' height='12' fill='{palette[category]}'></rect>")
        parts.append(f"<text x='{x+17}' y='27' class='legend'>{escape(category)}</text>")
        x += 142
    for i, row in mix.iterrows():
        y = 58 + i * row_h
        x = left
        parts.append(f"<text x='8' y='{y + 16}' class='bar-label'>{escape(row['airline'])}</text>")
        for category in order:
            w = (width - left - 24) * float(row[category]) / 100
            if w:
                parts.append(f"<rect x='{x:.1f}' y='{y}' width='{w:.1f}' height='22' fill='{palette[category]}'></rect>")
                x += w
    parts.append("</svg>")
    return "\n".join(parts)


def hourly_heatmap_svg(hourly: pd.DataFrame) -> str:
    airlines = sorted(hourly["airline"].unique())
    hours = list(range(24))
    cell, left, top = 30, 230, 42
    width, height = left + len(hours) * cell + 30, top + len(airlines) * cell + 50
    max_value = max(hourly["delay_propagation_rate"].max(), 1.0)
    lookup = {(r.airline, int(r.arrival_hour)): float(r.delay_propagation_rate) for r in hourly.itertuples(index=False)}

    parts = [
        "<h3>When Delays Spread During The Day</h3>",
        "<p class='chart-note'>Each square is an arrival hour. Darker red means more late arrivals turned into late next departures.</p>",
        f"<svg viewBox='0 0 {width} {height}' role='img'>",
    ]
    for hour in hours:
        parts.append(f"<text x='{left + hour * cell + 8}' y='28' class='heat-label'>{hour}</text>")
    for i, airline in enumerate(airlines):
        y = top + i * cell
        parts.append(f"<text x='8' y='{y + 19}' class='bar-label'>{escape(airline)}</text>")
        for hour in hours:
            value = lookup.get((airline, hour), 0.0)
            opacity = 0.12 + 0.88 * (value / max_value)
            parts.append(f"<rect x='{left + hour * cell}' y='{y}' width='{cell-2}' height='{cell-2}' fill='{COLORS['red']}' opacity='{opacity:.2f}'></rect>")
            if value >= max_value * 0.70:
                parts.append(f"<text x='{left + hour * cell + 5}' y='{y + 18}' class='heat-value'>{value:.0f}</text>")
    parts.append(f"<text x='{left}' y='{height-12}' class='axis-label'>Hours use local airport time from the BTS file.</text>")
    parts.append("</svg>")
    return "\n".join(parts)


def explainers_html() -> str:
    items = [
        ("Turnaround", "The time between one plane landing and that same plane taking off again."),
        ("Tight turn", "A turnaround under 45 minutes. It can be efficient, but there is less room to recover from delays."),
        ("Idle turn", "A turnaround over 180 minutes. The plane is sitting for a long time between flights."),
        ("Delay propagation", "A late plane arrives, then its next flight also leaves late. This is delay spreading."),
        ("Recovery rate", "A late plane arrives, but the next flight still leaves on time. This is the operation catching up."),
        ("Airborne hours", "How many hours the average plane spends flying in a day. More flying usually means better aircraft use."),
    ]
    cards = "".join(f"<div class='definition'><b>{escape(k)}</b><p>{escape(v)}</p></div>" for k, v in items)
    return f"<section class='wide'><h3>Metric Translator</h3><p class='chart-note'>Plain-English definitions for the dashboard.</p><div class='definitions'>{cards}</div></section>"


def table_html(df: pd.DataFrame, columns: list[str], title: str, note: str, limit: int = 20) -> str:
    display = df[columns].head(limit).copy()
    display = display.rename(
        columns={
            "airline": "Airline",
            "turnarounds": "Turns",
            "aircraft_tracked": "Aircraft",
            "turns_per_aircraft": "Turns per Aircraft",
            "avg_daily_legs_per_aircraft": "Daily Legs per Aircraft",
            "avg_daily_airborne_hours": "Daily Flying Hours",
            "median_turnaround_minutes": "Typical Ground Minutes",
            "tight_turn_rate": "Tight Turn %",
            "idle_turn_rate": "Idle Turn %",
            "delay_propagation_rate": "Delay Spread %",
            "late_recovery_rate": "Recovery %",
            "Dest": "Airport",
            "DestCityName": "City",
            "avg_turnaround_minutes": "Avg Ground Minutes",
            "inbound_late_rate": "Inbound Late %",
            "route": "Inbound Route",
            "next_route": "Next Route",
            "avg_arrival_delay": "Avg Arrival Delay",
            "avg_next_departure_delay": "Avg Next Departure Delay",
        }
    )
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda v: f"{v:.1f}")
    header = "".join(f"<th>{escape(col)}</th>" for col in display.columns)
    rows = []
    for row in display.to_dict("records"):
        rows.append("<tr>" + "".join(f"<td>{escape(str(row[col]))}</td>" for col in display.columns) + "</tr>")
    return f"<section class='wide'><h3>{escape(title)}</h3><p class='chart-note'>{escape(note)}</p><table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table></section>"


def write_dashboard(turns: pd.DataFrame, carrier: pd.DataFrame, airport: pd.DataFrame, hourly: pd.DataFrame, routes: pd.DataFrame) -> None:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    carrier.to_csv(SUMMARY_DIR / "carrier_operating_profile_expanded.csv", index=False)
    airport.to_csv(SUMMARY_DIR / "carrier_airport_bottlenecks_expanded.csv", index=False)
    hourly.to_csv(SUMMARY_DIR / "carrier_hourly_risk_expanded.csv", index=False)
    routes.to_csv(SUMMARY_DIR / "carrier_route_pair_risk.csv", index=False)

    kpis = [
        ("Aircraft Turns", f"{len(turns):,}", "One plane landing, waiting, then leaving again."),
        ("Planes Tracked", f"{turns['Tail_Number'].nunique():,}", "Unique aircraft tail numbers in the data."),
        ("Airlines", f"{turns['airline'].nunique():,}", "Airlines included in April 2026."),
        ("Typical Ground Time", f"{turns['turnaround_minutes'].median():.0f} min", "The middle turnaround time."),
        ("Tight Turns", f"{rate(turns['tight_turn_flag']):.1f}%", "Turns under 45 minutes."),
        ("Delay Spread", f"{rate(turns['delay_propagated_flag']):.1f}%", "Late arrival followed by late next departure."),
        ("Average Ground Time", f"{turns['turnaround_minutes'].mean():.0f} min", "Average time between arrival and next departure."),
        ("Idle Turns", f"{rate(turns['idle_turn_flag']):.1f}%", "Turns over 3 hours."),
    ]
    kpi_html = "".join(metric_card(*kpi) for kpi in kpis)

    highest_airports = airport.sort_values("delay_propagation_rate", ascending=False)
    riskiest_routes = routes.sort_values("delay_propagation_rate", ascending=False)
    best_recovery = carrier.sort_values("late_recovery_rate", ascending=False)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Aircraft Turnaround Carrier Analysis</title>
<style>
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #f5f7fb; color: {COLORS["ink"]}; }}
header {{ background: {COLORS["navy"]}; color: white; padding: 34px 44px; }}
header h1 {{ margin: 0 0 10px; font-size: 32px; letter-spacing: 0; }}
header p {{ margin: 0; max-width: 1050px; line-height: 1.5; }}
main {{ padding: 26px 42px 48px; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.kpi, section {{ background: white; border: 1px solid #d9e0ea; border-radius: 8px; }}
.kpi {{ padding: 14px; }}
.kpi span {{ display: block; color: {COLORS["gray"]}; font-size: 12px; text-transform: uppercase; }}
.kpi strong {{ display: block; font-size: 25px; margin-top: 4px; }}
.kpi p, .chart-note {{ color: {COLORS["gray"]}; font-size: 13px; line-height: 1.4; margin: 7px 0 0; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.wide {{ grid-column: 1 / -1; }}
section {{ padding: 18px; overflow-x: auto; }}
h2 {{ margin: 26px 0 12px; font-size: 21px; }}
h3 {{ margin: 0 0 8px; font-size: 17px; }}
svg {{ width: 100%; height: auto; }}
.axis {{ stroke: #9aa5b1; stroke-width: 1; }}
.axis-label, .axis-title, .legend {{ fill: {COLORS["gray"]}; font-size: 12px; }}
.bar-label, .point-label, .heat-label {{ fill: {COLORS["ink"]}; font-size: 12px; }}
.bar-value {{ fill: {COLORS["ink"]}; font-size: 12px; font-weight: bold; }}
.heat-value {{ fill: white; font-size: 10px; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px 9px; text-align: left; white-space: nowrap; }}
th {{ background: #f3f6fa; color: {COLORS["gray"]}; text-transform: uppercase; font-size: 11px; }}
.definitions {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; }}
.definition {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #fbfcfe; }}
.definition p {{ margin: 6px 0 0; color: {COLORS["gray"]}; font-size: 13px; line-height: 1.4; }}
</style>
</head>
<body>
<header>
<h1>Aircraft Turnaround Efficiency by Airline</h1>
<p>This dashboard follows each aircraft by tail number. It asks a simple question: after a plane lands, how quickly and reliably does that same plane leave again? Airline codes are expanded everywhere, so Spirit Airlines appears as Spirit Airlines (NK), Southwest as Southwest Airlines (WN), and so on.</p>
</header>
<main>
<div class="kpis">{kpi_html}</div>
<div class="grid">
{explainers_html()}
<section>{scatter_svg(carrier)}</section>
<section>{bar_svg(carrier, "airline", "delay_propagation_rate", "Which airlines let delays spread the most?", "A delay spreads when a late arriving aircraft also makes its next flight leave late.")}</section>
<section>{bar_svg(carrier, "airline", "tight_turn_rate", "Which airlines schedule the most short turns?", "A short turn is under 45 minutes on the ground. This can be efficient, but risky.")}</section>
<section>{bar_svg(carrier, "airline", "avg_daily_airborne_hours", "Which airlines keep aircraft flying the most?", "More airborne hours means the average aircraft spends more of the day in the air.", suffix=" hrs")}</section>
<section>{bar_svg(best_recovery, "airline", "late_recovery_rate", "Which airlines recover late arrivals best?", "Recovery means the aircraft arrived late, but its next flight still left on time.")}</section>
<section>{bar_svg(carrier, "airline", "idle_turn_rate", "Which airlines have more long ground waits?", "Idle turns are over 180 minutes. Some are planned, but too many can suggest unused aircraft time.")}</section>
<section class="wide">{turnaround_mix_svg(turns)}</section>
<section class="wide">{hourly_heatmap_svg(hourly)}</section>
{table_html(carrier, ["airline", "turnarounds", "aircraft_tracked", "turns_per_aircraft", "avg_daily_legs_per_aircraft", "avg_daily_airborne_hours", "median_turnaround_minutes", "tight_turn_rate", "idle_turn_rate", "delay_propagation_rate", "late_recovery_rate"], "Airline Scorecard", "This table gives each airline a plain-language operating profile.")}
{table_html(highest_airports, ["airline", "Dest", "DestCityName", "turnarounds", "avg_turnaround_minutes", "tight_turn_rate", "inbound_late_rate", "delay_propagation_rate"], "Highest-Risk Airline-Airport Combinations", "These are the airports where an airline's arriving aircraft most often carry delay into the next flight.", 35)}
{table_html(riskiest_routes, ["airline", "route", "next_route", "Dest", "turnarounds", "avg_turnaround_minutes", "tight_turn_rate", "delay_propagation_rate", "avg_arrival_delay", "avg_next_departure_delay"], "Riskiest Inbound-to-Outbound Aircraft Rotations", "This shows the actual route pair: where the aircraft came from, where it turned, and where it went next.", 35)}
</div>
</main>
</body>
</html>"""
    (PROJECT_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    turns = load_turns()
    carrier = build_carrier_summary(turns)
    airport = build_airport_summary(turns)
    hourly = build_hourly_summary(turns)
    routes = build_route_summary(turns)
    write_dashboard(turns, carrier, airport, hourly, routes)
    print(f"Wrote dashboard to {PROJECT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
