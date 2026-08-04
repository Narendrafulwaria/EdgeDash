"""
MockFetcher — returns 12 realistic fake job listings without any network calls.

4 of the 12 listings have hard-coded stable IDs so that running the cycle
twice proves deduplication: the second run should report 0 new rows for those 4.
"""
from __future__ import annotations

import types
from datetime import datetime, timezone

from edgedash.agents.base import Agent, AgentResult
from edgedash.config import Config
from edgedash.storage import make_listing_id

# ---------------------------------------------------------------------------
# Stable listings  (same id every run — used to prove dedup)
# ---------------------------------------------------------------------------

_STABLE: list[dict] = [
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-swiggy-001",
        "title": "Data Analyst",
        "company": "Swiggy",
        "location": "Bengaluru",
        "description": (
            "Analyse order-funnel data using SQL and Python. Build dashboards "
            "in Tableau. Partner with product teams to surface actionable insights. "
            "2+ years experience, strong statistics background required."
        ),
        "posted_at": "2026-07-28",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/ba-flipkart-002",
        "title": "Business Analyst",
        "company": "Flipkart",
        "location": "Bengaluru",
        "description": (
            "Own reporting for the supply-chain vertical. Advanced Excel, SQL, "
            "and Power BI essential. Drive A/B test analysis and present findings "
            "to senior leadership. 1–3 years experience."
        ),
        "posted_at": "2026-07-29",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-meesho-003",
        "title": "Data Analyst – Growth",
        "company": "Meesho",
        "location": "Bengaluru",
        "description": (
            "Deep-dive into user acquisition and retention metrics. Tools: Python "
            "(pandas, matplotlib), SQL, Looker. You will own dashboards consumed "
            "by the CMO. Entry to mid-level role."
        ),
        "posted_at": "2026-07-30",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/senior-da-razorpay-004",
        "title": "Senior Data Analyst",
        "company": "Razorpay",
        "location": "Bengaluru",
        "description": (
            "Lead analytics for the payments risk team. Requires 5+ years with "
            "Python, SQL, Spark, and experience building ML-feature pipelines. "
            "Mentor junior analysts; own the data-quality framework."
        ),
        "posted_at": "2026-07-27",
    },
]

# ---------------------------------------------------------------------------
# Varying listings  (url changes so id changes each seeding, but content is
# realistic — in real usage these would arrive fresh from the API)
# ---------------------------------------------------------------------------

_VARYING: list[dict] = [
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-phonepe-005",
        "title": "Data Analyst – Merchant Success",
        "company": "PhonePe",
        "location": "Bengaluru",
        "description": (
            "Analyse merchant onboarding funnels and payments data. Strong SQL "
            "and Python skills needed. Experience with Redash or Metabase a plus."
        ),
        "posted_at": "2026-08-01",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-zomato-006",
        "title": "Data Analyst – Restaurant Intelligence",
        "company": "Zomato",
        "location": "Bengaluru",
        "description": (
            "Build and maintain restaurant-performance scorecards. Proficiency in "
            "SQL and Excel required; Python and Tableau preferred."
        ),
        "posted_at": "2026-08-02",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/jr-da-byju-007",
        "title": "Junior Data Analyst",
        "company": "BYJU'S",
        "location": "Bengaluru",
        "description": (
            "First analytics role. You will write SQL queries, maintain reports "
            "in Google Sheets, and assist senior analysts. 0–1 year experience. "
            "Knowledge of Python is a bonus."
        ),
        "posted_at": "2026-08-03",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-ola-008",
        "title": "Data Analyst – Driver Operations",
        "company": "Ola",
        "location": "Bengaluru",
        "description": (
            "Own operational metrics for driver supply and demand forecasting. "
            "Heavy SQL, Python (numpy/pandas), and strong communication skills. "
            "3 years experience preferred."
        ),
        "posted_at": "2026-07-31",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/analytics-engineer-cred-009",
        "title": "Analytics Engineer",
        "company": "CRED",
        "location": "Bengaluru",
        "description": (
            "Bridge the gap between data engineering and BI. dbt, SQL, Python, "
            "and Looker. Build modular data models consumed by 10+ analysts. "
            "2–4 years experience."
        ),
        "posted_at": "2026-08-01",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-navi-010",
        "title": "Data Analyst – Credit Risk",
        "company": "Navi Technologies",
        "location": "Bengaluru",
        "description": (
            "Develop risk scorecards and portfolio-monitoring dashboards. SQL, "
            "Python, and basic ML literacy required. Fintech background a plus."
        ),
        "posted_at": "2026-08-02",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/lead-da-dunzo-011",
        "title": "Lead Data Analyst",
        "company": "Dunzo",
        "location": "Bengaluru",
        "description": (
            "Lead a team of 3 analysts. Own end-to-end analytics for the "
            "dark-store network. Requirements: 6+ years, Python, SQL, "
            "Tableau, stakeholder management."
        ),
        "posted_at": "2026-07-28",
    },
    {
        "source": "mock",
        "url": "https://jobs.example.com/da-urban-company-012",
        "title": "Data Analyst – Partner Experience",
        "company": "Urban Company",
        "location": "Bengaluru",
        "description": (
            "Analyse service-partner performance and earnings data. Produce "
            "weekly insights decks for operations leadership. SQL and Excel "
            "required; Power BI experience valued. 1–2 years experience."
        ),
        "posted_at": "2026-08-03",
    },
]


def _build_rows(fetched_at: str) -> list[dict]:
    rows = []
    for item in _STABLE + _VARYING:
        row = dict(item)
        row["id"] = make_listing_id(row["source"], row["url"])
        row["fetched_at"] = fetched_at
        rows.append(row)
    return rows


class MockFetcher:
    name: str = "mock_fetcher"

    def run(self, config: Config, storage: types.ModuleType) -> AgentResult:
        fetched_at = datetime.now(timezone.utc).isoformat()
        rows = _build_rows(fetched_at)

        try:
            new_count = storage.upsert_listings(rows)
        except Exception as exc:
            return AgentResult(
                agent=self.name,
                status="failed",
                records_touched=0,
                notes=f"upsert failed: {exc}",
            )

        total = len(rows)
        duplicate_count = total - new_count
        return AgentResult(
            agent=self.name,
            status="ok",
            records_touched=new_count,
            notes=(
                f"presented {total} listings — "
                f"{new_count} new, {duplicate_count} duplicate (skipped)"
            ),
        )
