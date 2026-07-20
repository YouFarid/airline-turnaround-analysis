# SQL Workflow

## PostgreSQL Workflow

Use these files in order:

1. `01_schema_postgres.sql`
   - Creates the staging table and typed analysis table.
2. `02_load_bts_csv_postgres.psql`
   - Uses `\copy` to load the BTS CSV from your Downloads folder.
   - Converts the staging rows into typed columns.
   - Adds indexes for tail-number sequencing and summaries.
3. `03_turnaround_model_postgres.sql`
   - Creates `v_completed_flights`.
   - Creates `v_aircraft_turnarounds`.
4. `04_kpi_queries_postgres.sql`
   - Contains the analysis queries for Tableau worksheets and portfolio screenshots.

The main analytical object is:

`v_aircraft_turnarounds`

That view has one row per valid aircraft turn.

## SQLite Files

The older SQLite files are kept for reference:

- `01_schema_sqlite.sql`
- `02_turnaround_model.sql`
- `03_kpi_queries.sql`

For your setup, use the PostgreSQL files instead.
