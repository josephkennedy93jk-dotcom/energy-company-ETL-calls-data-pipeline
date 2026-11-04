<p align="center"><img src="project%20images/s-power-logo-horizontal.png" width="320" alt="S-Power"></p>

# Call Centre AI Data Pipeline

*Turning raw call-centre AI output into clean, joined, reportable data.*

![Python](https://img.shields.io/badge/Python-pandas-3776AB?style=flat-square) ![Cloud Storage](https://img.shields.io/badge/Google%20Cloud-Storage-4285F4?style=flat-square) ![BigQuery](https://img.shields.io/badge/Warehouse-BigQuery-669DF6?style=flat-square) ![Power BI](https://img.shields.io/badge/BI-Power%20BI-F2C811?style=flat-square)

S-Power is a fictional energy retailer made for this portfolio. It is not affiliated with any real company, and the data is synthetic.

---

## 1. The Business Case

S-Power is rolling out a new call centre AI (CCAI) system in its telesales team. The system writes a JSON file for every call. The CRM holds the sales outcomes in a separate export. Nothing joined the two, and nothing checked either.

S-Power needs help using the data that comes out of the new system. This project builds that data layer: collect the CCAI output, clean it, join it to sales, and report on it.

## 2. Headline Results

| Measure | Value |
| ------- | ----- |
| Calls processed | 1,000 |
| Sales / conversion rate | 242 / 24.2% |
| Total order value | £220,760 |
| Calls with all 3 compliance disclosures | 63.9% |
| Sales made on a call with a missed disclosure | 93 of 242 (38%) |

The weakest disclosure is the exit fee, given on 78.7% of calls.

## 3. The Pipeline

![Pipeline](project%20images/pipeline_C_hybrid.png)

| Stage | Script | What it does |
| ----- | ------ | ------------ |
| Raw | `00_call_json_raw.py` | Generates the 1,000 synthetic call JSON files |
| Bronze | `01_extract_calls_bronze.py` | Reads every JSON into one table, one row per call |
| Silver | `02_clean_calls_silver.py` | Fixes data issues, quarantines what it can't fix, logs every action |
| Load | `03_load_callsdata_cloud.py` | Uploads raw, bronze and silver files to Cloud Storage |
| Run all | `run_pipeline.py` | Runs the stages in order |

![Pipeline run](project%20images/pipeline_run_output.png)

**Data quality.** The cleaning step found two kinds of problem:
- `C0199` appeared twice. The second file is `C0199_200.json`, so the ID was replaced from the filename.
- `C0050` and `C0120` had no `agent_id`, so they were set to `unknown`.

All three actions are in `calls_cleaning_log.csv`. Result: 1,000 rows in, 1,000 rows in silver, nothing lost. The quarantine table is empty because both issues could be repaired.

## 4. Cloud and Warehouse

- Bucket `calls_storage_energy` (EU, not public) holds `raw`, `bronze` and `silver` folders.
- BigQuery datasets `silver_calls` and `crm_data`, both in the EU. The CRM data was first loaded into a US dataset by mistake and recreated in the EU so the tables could be joined.
- Join check on `call_id` passed with 1,000 matching rows (`table join.sql`).

![Schema](project%20images/simple-schema-project.png)

## 5. Power BI Dashboard

Built on the silver data with a custom S-Power theme. connection in production would be from BigQuery Gold table to BI software for semantic model design. 

### Sales performance

![Sales dashboard](project%20images/S-Power-sales%20performance-dash.png)

**Agent revenue and conversion rate.** Order value won by each agent next to their conversion rate. Shows who sells the most and who converts best.

![Agent revenue and conversion rate](project%20images/Agent-Revenue-and-conversion-rate.png)

**Agent metrics table.** Calls, sales, conversion and order value per agent in one place, for comparing agents.

![Agent metrics table](project%20images/Agent-metrics-table.png)

**Customer intent ratio.** What customers called about. Intent shapes the outcome of the call.

![Customer intent ratio](project%20images/Customer-Intent%20-Ratio.png)

**Value by campaign.** Total order value from each campaign. Shows which campaigns earn the most.

![Value by campaign](project%20images/value-generated-by-campaign.png)

### Compliance and call quality

![Compliance dashboard](project%20images/S-Power-Quality-compliance-dash.png)

- **Disclosure cards.** Share of calls where the exit fee (78.7%), cancellation rights (90.5%) and recording notice (90.9%) were given.
- **Calls by number of misses.** 639 calls with no miss, 325 with one, 34 with two, 2 with three.
- **Sales with a miss.** 93 of the 242 sales were made on a call where at least one disclosure was missed.

**Fully compliant calls by hour.** Compliance rate across the working day. Shows when agents are most likely to miss a disclosure.

![Fully compliant calls by hour](project%20images/fully-compliant-calls-hours-day.png)

**Caveats.** Calls in this synthetic data last 15 to 59 seconds, much shorter than real calls. Sentiment looks like an outcome of the call, not a cause of the sale, so it is shown as "what a good call looks like".

## 6. What I'd Do Next

**Finish what is planned**
- Build gold tables in BigQuery with SQL (conversion by agent, compliance by campaign)
- Connect Power BI to the gold tables
- Load silver into BigQuery automatically instead of through the console
- Keep dated folders in the bucket so each run is kept, not overwritten

**Tools I'd consider at production scale** (not used here, because 1,000 files don't need them)
- **Airflow or Cloud Composer** to schedule and monitor the stages, with retries and alerts
- **dbt or Dataform** to manage the silver-to-gold SQL, with built-in tests and documentation
- **Data quality tests** (dbt tests or Great Expectations) to replace my hand-written checks
- **Event-driven loading** so a new call file in the bucket triggers the pipeline, instead of a manual run
- **Real CCAI output** in place of synthetic data, with personal data kept out of the analytics layers

## 7. Repository Contents

| Item | Purpose |
| ---- | ------- |
| `python Files/` | Pipeline scripts (00 to 03 plus `run_pipeline.py`) |
| `CSV FILES/` | Bronze, silver, quarantine, cleaning log and CRM export |
| `JSON Raw Call Files/` | Raw call files (sample) |
| `table join.sql` | BigQuery join check |
| `calls sales dashboard.pbix` | Power BI report |
| `S-Power KPI Dash.pdf` | Dashboard export |
| `S-Power_DAX_measures.txt` | DAX measures used in the report |
| `project images/` | Diagrams, dashboard screenshots and branding |

## 8. How to Reproduce

1. Run `python Files/run_pipeline.py`, or the numbered scripts in order
2. Load the silver CSV and `crm_export.csv` into BigQuery (EU datasets)
3. Open `calls sales dashboard.pbix`

Needs Python 3.10+ with `pandas`, `google-cloud-storage` and `google-cloud-bigquery`, and a Google Cloud project with a bucket.

## 9. Author

**Joseph Kennedy**. Built to show a Python pipeline, cloud storage, BigQuery and Power BI working together on call-centre data.
