# Data Notes

The original BTS flight file is not included in this repo because it is large.

Download it from BTS TranStats:

`On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2026_4.csv`

This project used April 2026 Reporting Carrier On-Time Performance data.

Expected local folder if you use the scripts without changing anything:

`C:\Users\monae\Downloads\On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_4\`

If your CSV is somewhere else, set an environment variable before running:

```powershell
$env:BTS_CSV_PATH="C:\path\to\your\bts_file.csv"
python scripts\build_tableau_outputs.py
```

## What is included

The `data/summary` folder contains smaller summary CSVs used for the dashboard and review:

- airline scorecard
- airline-airport risk pockets
- hourly risk table
- risky aircraft route-pair rotations

## What is not included

The generated turn-level file is not committed:

`data/processed/tableau_aircraft_turnarounds_april_2026.csv`

That file is useful for Tableau, but it is too large for a normal GitHub upload.

