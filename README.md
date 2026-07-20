# Airline Turnaround Analysis

This is a data analysis project about aircraft turnaround efficiency.

The basic question:

**After a plane lands, how quickly and reliably does that same plane leave again?**

I used U.S. BTS flight data, SQL, Python, and Tableau-style dashboarding to rebuild aircraft rotations from tail numbers. The project looks at ground time, short turns, long idle waits, and whether a late arriving aircraft makes the next flight late too.

Live dashboard file:

`index.html`

If this repo is deployed with GitHub Pages, that file becomes the homepage.

## Why I Built This

I wanted an aviation analytics project that felt closer to real airline operations than a basic "flight delays by month" chart.

Aircraft only make money when they are flying, but airlines also need enough ground time to unload, board, fuel, clean, handle bags, and recover from delays. That tradeoff is what this project studies.

## Main Findings From April 2026

- 597,919 raw flight records
- 433,812 valid same-aircraft turnarounds rebuilt
- 5,699 aircraft tracked by tail number
- 13 airlines included
- typical ground time was 61 minutes
- average ground time was 78 minutes
- 18.5% of turns were under 45 minutes
- 3.9% of turns were over 180 minutes
- 12.7% of turns had delay propagation

In plain English, delay propagation means:

> a plane arrived late, and then that same plane's next flight also left late.

## Dashboard

Open:

`index.html`

The dashboard includes:

- airline risk map
- delay spread by airline
- short-turn rate by airline
- aircraft flying hours by airline
- late-arrival recovery rate
- long ground-wait rate
- ground time mix
- time-of-day delay heatmap
- airline scorecard
- highest-risk airline-airport combinations
- riskiest inbound-to-outbound aircraft rotations

Airline codes are expanded in the dashboard, so instead of only seeing `NK`, the page shows `Spirit Airlines (NK)`.

## Project Structure

```text
.
├── index.html
├── data
│   ├── README.md
│   └── summary
├── docs
├── scripts
│   ├── build_tableau_outputs.py
│   └── build_carrier_dashboard.py
└── sql
```

## How To Rebuild It

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Download the BTS April 2026 CSV and either put it in the default Downloads folder or set:

```powershell
$env:BTS_CSV_PATH="C:\path\to\your\bts_file.csv"
```

Build the turn-level data:

```powershell
python scripts\build_tableau_outputs.py
```

Build the website:

```powershell
python scripts\build_carrier_dashboard.py
```

The website will be written to:

```text
index.html
```

## PostgreSQL

The `sql` folder has the PostgreSQL workflow:

1. `01_schema_postgres.sql`
2. `02_load_bts_csv_postgres.psql`
3. `03_turnaround_model_postgres.sql`
4. `04_kpi_queries_postgres.sql`
5. `05_carrier_deep_dive_postgres.sql`

The most important SQL idea is the window function that links one aircraft's current flight to its next flight:

```sql
LEAD(actual_departure_ts) OVER (
    PARTITION BY tail_number, flightdate
    ORDER BY scheduled_departure_ts, actual_departure_ts
)
```

That is how the project turns flight rows into aircraft rotations.

## Tableau

The generated turn-level CSV can be connected to Tableau:

`data/processed/tableau_aircraft_turnarounds_april_2026.csv`

That file is generated locally and ignored by GitHub because it is large.

The `docs` folder includes Tableau dashboard notes and calculated fields.

