# EdgeDash

EdgeDash is an autonomous career intelligence agent that runs on a daily schedule.
It fetches live job listings from configured sources, scores each listing for fit
against your skills profile, identifies the skill gaps most likely to be holding
you back, verifies its own output, and publishes the results to a Streamlit
dashboard — all without manual intervention.

## Architecture

```
Trigger (scheduled)
        |
        v
  Orchestrator
   |          |          |
   v          v          v
Fetcher    Scorer   GapAnalyzer
        \     |     /
         v   v   v
          Verifier
             |
             v
           Storage
             |
             v
        Dashboard (read-only)
```

The Orchestrator reads state and delegates. It never fetches or scores directly.
Each sub-agent has one goal and one stop condition.
The Dashboard only reads from Storage — it never writes.

## Current status

### Built (week 1)

- [x] `edgedash/config.py` — `Config` dataclass, loads from `config.yaml`, fails loudly if absent
- [x] `edgedash/storage.py` — the only module allowed to touch SQLite; thin interface designed for a one-file swap to Postgres
- [x] `edgedash/_schema.py` — DDL for `listings`, `skill_gaps`, `cycle_log`
- [x] `edgedash/agents/base.py` — `Agent` protocol and `AgentResult` dataclass
- [x] `edgedash/agents/mock_fetcher.py` — **temporary** mock; returns 12 hard-coded listings with 4 stable ids to prove deduplication
- [x] `edgedash/orchestrator.py` — reads state, prints plan with reasons, runs agents, logs every run to `cycle_log`, prints cycle summary
- [x] `run_cycle.py` — entry point; exits 1 if any agent fails

### Coming — week 2

- [ ] Real `Fetcher` agent — live listings from a job-board API (replaces `MockFetcher`)
- [ ] `Scorer` agent — fit score (0–100) written back to the `listings` table

### Coming — week 3

- [ ] `GapAnalyzer` agent — populates `skill_gaps` table from unmatched listing requirements
- [ ] `Verifier` — validates cycle output before Storage is written

### Coming — week 4

- [ ] Streamlit `Dashboard` — read-only view of scored listings and gap trends
- [ ] Postgres migration — swap `storage.py` backend; no other file changes

## Setup

**Python 3.11 or later is required.**

```bash
# 1. Clone and enter the repo
git clone https://github.com/Narendrafulwaria/EdgeDash.git
cd EdgeDash

# 2. Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install pyyaml
```

Edit `config.yaml` to match your profile — set `target_role`, `target_city`,
`keywords`, `my_skills`, `experience_years`, and `min_fit_score`. Secrets
(API keys, DB connection strings) go in a `.env` file, never in `config.yaml`.

## Running

```bash
python run_cycle.py
```

The cycle prints:

1. Current state read from the database (last fetch time, unscored count)
2. The plan it chose and why
3. Each agent's result as it runs
4. A summary table with total records touched and any failures

Run it twice in a row to see deduplication in action — the second run reports
0 new listings because every id is already in the database.

## Design decisions

**Storage isolated behind one module.**
Every read and write goes through `edgedash/storage.py`. No other module imports
a database driver. When the SQLite backend is replaced with hosted Postgres in
week 4, only that one file changes — the rest of the codebase is unaffected.

**Listing IDs are stable hashes.**
Each listing's primary key is a SHA-256 hash of `source + url`. The same job
reappearing in a future fetch produces the same ID, so `INSERT OR IGNORE`
silently skips it. This makes deduplication observable: `upsert_listings`
returns the count of genuinely new rows, not the total passed in.

**The Orchestrator delegates instead of doing the work itself.**
Keeping fetch, score, and analysis logic out of the Orchestrator means each
concern is isolated, independently testable, and swappable. The Orchestrator
reads state, decides what to run, and reports results — a boundary that stays
stable even as the agents evolve week by week.
