# Architectural Review: Creator Audit Automation Platform

This document provides a comprehensive engineering review of the current `Audit-Agent` implementation and outlines the recommended path forward to build a scalable, production-ready internal platform.

## 1. CURRENT IMPLEMENTATION ANALYSIS

**Architecture & Flow**
The current application is a monolithic MVP built with Streamlit. The flow is highly synchronous:
1. User enters a username in the Streamlit UI (`app.py`).
2. Streamlit synchronously calls `scraper.py`, which launches a local Chrome instance via `undetected_chromedriver`.
3. The scraper navigates to NotJustAnalytics, waits for Cloudflare to pass, and injects JavaScript (`extractor.py`) to scrape the DOM.
4. The scraped data is returned to Streamlit and saved locally as `info.JSON`.
5. Streamlit synchronously calls `llm/client.py` to generate an audit via Gemini.
6. The report is rendered in the UI.

**Component Status**
*   **Existing & Used**: Streamlit UI (`app.py`), Scraper engine (`scraper.py`, `extractor.py`), AI integration (`llm/client.py`).
*   **Incomplete / Dead Code**: The `database/` folder (SQLAlchemy models) and `delivery/` folder (Email sending) exist but are **never imported or executed** in the main flow. 
*   **Patterns & Coupling**: The code is highly tightly coupled. The UI thread executes heavy browser automation directly. The scraper is deeply tied to the DOM structure of a single site (NotJustAnalytics).
*   **Production Readiness**: **Not production-friendly.** It is a local script disguised as a web app. Streamlit is designed for data dashboards, not for orchestrating heavy, long-running browser automation tasks.

---

## 2. SELENIUM IMPLEMENTATION REVIEW

**Current Usage & Quality**
The system uses `undetected_chromedriver` to bypass Cloudflare. This is a common and effective tactic for basic scraping, and it successfully evades simple bot detection. The extraction logic is injected via JS (which is a smart way to bypass some of Selenium's slow Python bindings).

**Weaknesses & Scalability**
*   **Synchronous Blocking**: The Streamlit app completely halts while Chrome runs. 
*   **Resource Heavy**: Selenium + full Chrome is incredibly heavy. If two employees run audits simultaneously, two full Chrome instances launch. 
*   **Brittle Selectors**: The `extractor.py` JS relies on regex text matching (`findBeforeLabel`) and generic DOM label scanning. If NotJustAnalytics changes their layout slightly, this will break silently or return garbage data.

**Selenium vs. Playwright**
For a modern, JS-heavy scraping project, **Playwright is vastly superior** to Selenium:
*   **Network Interception**: Instead of scraping the DOM (which breaks easily), Playwright can intercept the underlying XHR/Fetch API requests NotJustAnalytics makes to its backend, giving you pristine JSON data directly.
*   **Concurrency**: Playwright is built from the ground up for async/await in Python, handling multiple browser contexts in a single instance with drastically less memory overhead.
*   **Stability**: Playwright natively waits for elements to be actionable, eliminating the need for arbitrary `time.sleep()` calls currently scattered in `scraper.py`.
*   **Recommendation**: **Migrate to Playwright.** It is much easier to maintain, handles concurrency effortlessly, and is the industry standard for scalable automation.

---

## 3. DATABASE & DATA FLOW REVIEW

**Current State**
Currently, data flows from the scraper -> memory -> `info.JSON` -> Streamlit. 
There is a `models.py` file defining an SQLite database with a single `influencers` table, but it is not integrated.

**Database Review & Schema**
The current `models.py` uses a flat schema (one table holding everything). This violates normalization rules because influencer metadata (username, followers) is mixed with point-in-time audit metrics (engagement rate today vs. next month).
The project uses SQLite, which does not support concurrent writes well, contradicting the goal of PostgreSQL.

**Recommended Schema (PostgreSQL)**
1.  **`Influencers` Table**: `id`, `username`, `created_at` (Core identity)
2.  **`AuditRuns` Table**: `id`, `influencer_id`, `status` (pending, success, failed), `scraped_at` (Tracks the specific execution)
3.  **`Metrics` Table**: `id`, `audit_run_id`, `followers`, `engagement_rate`, `avg_likes`, etc. (The actual data for that run)
4.  **`Reports` Table**: `id`, `audit_run_id`, `ai_summary`, `pdf_url`

---

## 4. SCALABILITY REVIEW

If 5 employees use this simultaneously right now, **it will instantly crash**.
1.  **Streamlit Threading**: Streamlit runs scripts from top to bottom. 5 users mean 5 concurrent executions of `scraper.py`.
2.  **Memory Exhaustion**: 5 instances of `undetected_chromedriver` will consume several gigabytes of RAM. If deployed on a standard 2GB/4GB cloud instance, it will OOM (Out of Memory) crash immediately.
3.  **Anti-Patterns**: Running heavy synchronous tasks (Selenium) on a web server thread. 

---

## 5. RECOMMENDED FINAL ARCHITECTURE

To achieve the goal of a scalable, AWS-deployable internal tool, the architecture must transition to an asynchronous, queue-based system.

*   **Frontend**: Next.js or React (SPA). Users submit a username and get a "Loading/Processing" state while polling the backend for completion.
*   **Backend API**: FastAPI (Python). Fast, async natively, and perfect for kicking off jobs and serving status updates.
*   **Task Queue**: Celery + Redis (or AWS SQS). When a user requests an audit, FastAPI drops a message in Redis. A separate background worker picks it up.
*   **Scraper Engine**: Playwright Python running inside the Celery worker. Handles Cloudflare bypass (via stealth plugins) and intercepts network requests instead of scraping the DOM.
*   **Database**: PostgreSQL (managed via RDS on AWS) using SQLAlchemy async.
*   **AI Layer**: Gemini API called by the Celery worker after scraping finishes.
*   **Deployment (Docker)**: 
    *   Container 1: Next.js Frontend
    *   Container 2: FastAPI Backend
    *   Container 3: Celery Worker (with Playwright browser binaries installed)
    *   Container 4: Redis (Queue)
    *   Database: AWS RDS (Postgres)

---

## 6. MIGRATION PLAN

**Difficulty**: Moderate. You are essentially rebuilding the orchestration layer, but keeping the core logic.

1.  **Phase 1: Decouple (Low Effort)**: Separate Streamlit from scraping. Keep Streamlit, but have it write to a database, and run a separate script to process database rows.
2.  **Phase 2: Playwright Rewrite (Medium Effort)**: Rewrite `scraper.py` using `playwright-python`. Focus on intercepting API calls rather than parsing the DOM. *The `extractor.py` will likely be thrown away, replaced by clean JSON parsing.*
3.  **Phase 3: Queue Implementation (Medium Effort)**: Introduce FastAPI + Celery to handle the background jobs.
4.  **Phase 4: Frontend (High Effort)**: Replace Streamlit with a proper Next.js dashboard for employees.

**What can be reused**: The Gemini prompt (`llm/client.py`), the general concept of the data pipeline, and the metric calculations.

---

## 7. CODE QUALITY REVIEW

*   **Folder Structure**: Logical (`database`, `delivery`, `llm`), but currently misrepresentative since half the folders are dead code.
*   **Modularity**: Very poor. `app.py` acts as a controller, view, and orchestrator.
*   **Technical Debt**: High. The DOM extraction logic in JS is extremely brittle. Relying on Streamlit for task execution is a major architectural flaw for this use case.
*   **Security/Credentials**: The project correctly uses `.env` for `GOOGLE_API_KEY` and email credentials, which is good.

---

## 8. FINAL VERDICT

**Is the current implementation good?**
It is a successful **Proof of Concept (PoC)**, but it is **not** an MVP that can be scaled or safely deployed for a team.

*   **Well-designed**: The LLM prompt is clean, and the UI looks great visually. Using undetected-chromedriver was a smart choice to get past Cloudflare quickly.
*   **Problematic**: Synchronous blocking architecture, heavy memory footprint, unintegrated database, brittle DOM scraping.
*   **Immediately Refactor**: Move the scraping execution OUT of the Streamlit request lifecycle. Implement a background queue immediately, even if it's just a simple threading queue for now.
*   **Long-term Quality**: To achieve the vision of an AI-powered creator automation platform, the architecture must shift to FastAPI + Celery + Playwright. Attempting to scale the current Streamlit + Selenium setup will result in endless server crashes and failed audits.
