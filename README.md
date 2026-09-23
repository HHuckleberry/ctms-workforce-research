# CTMS Workforce Report

An interactive report on DHS's Cybersecurity Talent Management System (CTMS) —
population, pay, promotions, retention, and individual career trajectories —
built entirely from [OPM's public open-data API](https://data.opm.gov). No
API key, account, or special access required; the data is public.

## Quick start

```bash
python3 run.py
```

(or double-click `run.command` on macOS/Linux, `run.bat` on Windows)

That's it. This one command:

1. Creates a local virtual environment (`.venv/`)
2. Installs the three dependencies it needs (`requests`, `pandas`, `pyarrow`)
3. Pulls CTMS workforce data from OPM going back to the program's actual
   inception (June 2022), calculating the same-component 2210 comparison
   during the same employment download pass
4. Reconstructs individual employee timelines from the de-identified data
   (OPM's public data has no employee ID — see [Methodology](#methodology))
5. Validates population rules, version state, reconstructed histories, and
   comparison totals; failed checks stop the build
6. Builds the report and opens it in your browser

The first pull takes **15–20 minutes** on a normal connection. Later runs are
incremental: they record the OPM version used for every month, download only
new or revised snapshots, and rebuild the report from the cached local CSVs.
A typical monthly update therefore downloads one new month per dataset instead
of the full history. Revised snapshots replace their prior rows rather than
being appended, and output files are written atomically so an interrupted run
can be rerun safely without duplicating a month.

For an unattended scheduled run, use:

```bash
python3 run.py --no-open
```

## Public report

The current interactive report is published with GitHub Pages at:

<https://hhuckleberry.github.io/ctms-workforce-research/>

After a monthly update, publish the newly generated report with:

```bash
python3 run.py --no-open
python3 publish.py
```

`publish.py` sends only the generated standalone HTML file to the dedicated
`gh-pages` branch. Generated data remains ignored on the source branch.

Use `python3 run.py --full-refresh` when you intentionally want to rebuild the
entire historical baseline, such as after changing the CTMS population rule.
Routine runs detect OPM revisions automatically.

The production population is pay plan `DC` or `DL` intersected with the
DHS-only cybersecurity series family: `2212`, `2213`, `2218`, `2221`, `2224`,
`2225`, `2226`, `2228`, `2229`, and `2230`. On every newly downloaded month,
the pull audits all DC/DL records by occupational series and warns if another
code appears.

## What you get

A single self-contained HTML report (`report/ctms_workforce_report.html`)
with:

- Headcount, pay, and turnover trends since program inception
- A year-by-year pay-raise explorer — every January cycle's actual
  distribution of individual raises, not just an average
- Click-through drill-down from any chart or number straight to the
  underlying people, and from any person to their full trajectory
  (salary history chart + event timeline)
- Comparison against the standard federal IT-management track (series 2210)
  inside the same fixed set of components that use CTMS, calculated without a
  second employment download
- Component-adoption and occupational-series monitoring, including a review
  flag for any DHS DC/DL series outside the current population rule
- A refresh-validation summary reconciling raw counts, reconstructed histories,
  comparison totals, schemas, and OPM snapshot versions
- Pay-plan-by-component (subelement) and pay-spread breakdowns
- Retention factors — prior federal experience, relocation, veteran status,
  tenure-group mix over time, and time-to-promotion, each checked against
  the data rather than assumed
- Estimated salary represented by observed CTMS tenure: one-twelfth of each
  observed person-month's annualized adjusted basic pay. This is an evidence-
  based estimate from OPM snapshots, not a payroll-ledger total.
- Sourced findings from GAO, DHS's Inspector General, and congressional
  testimony, cross-checked against the OPM data wherever they overlap
- A search box, sortable/filterable table with per-person sparklines, and
  CSV export
- Print/PDF-ready view

Open the HTML file in any browser — it's fully self-contained, no server
needed.

## Project structure

```
run.py                          one-command orchestrator (see Quick start)
requirements.txt
pull/
  opm_ctms_pull.py              step 1: pull raw data from data.opm.gov
  ctms_track_individuals.py     step 2: reconstruct individual timelines
  ctms_validate.py              step 3: validate and reconcile pipeline outputs
  ctms_report_data.py           step 4: build the consolidated report JSON
report/
  template.html                short shell defining layout and include order
  sections/                    HTML sections (people table, methodology, etc.)
  styles/report.css            report styling, responsive and print rules
  scripts/                     JavaScript grouped by chart and feature
  ctms_workforce_report.html    generated output - open this
```

You can also run the three pipeline scripts individually (from inside
`pull/`, using the venv's Python) if you want to inspect the intermediate
CSVs — each step's output and purpose is documented in its own file header.

## Editing the report

Edit the source files under `report/sections/`, `report/styles/`, and
`report/scripts/`. `report/template.html` controls their order using
`{{ include "sections/headcount-section.html" }}` directives. Include paths
are relative to `report/`; the build inlines each file's contents, including
its whitespace. JavaScript files share the existing script scope and execute
in template order, so keep shared helpers before their consumers.

Rebuild after HTML, CSS, or JavaScript edits using the existing report JSON:

```bash
python3 run.py --build-only --no-open
```

This command requires `pull/ctms_report_data.json` from a prior pipeline run.
It skips dependency installation, data downloads, and data calculations.
For changes to Python calculations, run the affected pipeline stages first.
The generated `report/ctms_workforce_report.html` still embeds all report
code and data in one file for sharing; do not edit that generated file.

## Methodology

OPM's public workforce data is deliberately de-identified — no names, no
employee IDs. Individuals in this report are reconstructed from a composite
key (service computation date + duty station + age bracket + education
level), which is unique within a single month but can drift for the same
real person over time (an age bracket ticks over, a relocation, a degree
finished). A linking pass reconnects drifted records under strict
conditions, and a second validation pass catches and undoes any merge that
would put two people in the same month — full details and the exact rules
are documented as comments in `pull/ctms_track_individuals.py`, and
summarized in the report's own Methodology section.

The month attached to a person or cohort is the first monthly snapshot in
which that reconstructed person appears, not a known appointment date. For
example, "first observed Dec 2022" normally means absent from the November
snapshot and present in the December snapshot; the actual CTMS entry occurred
somewhere in that interval. People already present in the first available
snapshot are left-censored, so their entry interval is unknown.

Treat individual-level results as a well-evidenced best reconstruction, not
verified ground truth. Population-level aggregates (headcount, medians,
totals) are not affected by this — they come directly from the raw pulled
data.

## License

The code here is provided as-is for anyone to run and adapt. The underlying
data is public information from OPM (data.opm.gov).
