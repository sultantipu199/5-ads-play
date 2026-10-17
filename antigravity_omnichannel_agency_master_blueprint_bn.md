# Antigravity Omnichannel Autonomous Agency Engine

## Production-Grade Master Blueprint, Implementation Plan, Fixes, and Antigravity Orchestration Playbook

**ভাষা:** বাংলা  
**লক্ষ্য:** Meta, Google Ads, LinkedIn, TikTok এবং Snapchat-এর ডেটা সংগ্রহ, বিশ্লেষণ, নীতিমালা যাচাই, সুপারিশ, অনুমোদিত পরিবর্তন এবং Telegram briefing-কে একটি নিরাপদ, পর্যবেক্ষণযোগ্য ও ধাপে ধাপে স্বয়ংক্রিয় সিস্টেমে রূপান্তর করা।  
**গুরুত্বপূর্ণ নীতি:** প্রথম সংস্করণে read-only, পরের ধাপে human approval, সবশেষে সীমিত ও reversible autonomy। কখনোই শুরু থেকে unrestricted auto-spend বা auto-pause চালু করা যাবে না।

---

## 1. বর্তমান ব্লুপ্রিন্টের সৎ মূল্যায়ন

বর্তমান ধারণাটি ভালো prototype, কিন্তু এখনো production-ready autonomous agency engine নয়। প্রধান ঘাটতি:

1. `main_agency_runner.py` বাস্তবে কোনো agent orchestration বা API call করে না, শুধু status print করে।
2. Telegram report-এর spend, lead ও CPA hard-coded। এগুলো live data নয়।
3. `clients.json`-এ account ID রাখা গেলেও OAuth lifecycle, token refresh, scopes, revocation, rotation নেই।
4. Keyring ব্যবহার করলেই সব পরিবেশে encryption-at-rest নিশ্চিত হয় না। Headless server, Docker এবং CI-তে backend আলাদা হতে পারে।
5. Cross-platform metric normalization নেই। যেমন conversion, attribution window, currency এবং timezone platformভেদে আলাদা।
6. Retry থাকলেও idempotency, rate-limit header parsing, per-platform concurrency এবং dead-letter queue নেই।
7. Agent output-এর schema, evidence, confidence, consensus rule এবং conflict resolution নেই।
8. Budget পরিবর্তনের আগে approval, dry-run, rollback, maximum delta এবং audit trail নেই।
9. Test, staging, observability, deployment এবং incident response অনুপস্থিত।
10. “শতভাগ autonomous” দাবি বাস্তবসম্মত বা নিরাপদ নয়। Production লক্ষ্য হওয়া উচিত **bounded autonomy**।

---

## 2. Target Architecture

```text
omnichannel-enterprise-engine/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── config/
│   ├── clients.example.yaml
│   ├── policies.yaml
│   ├── metric_map.yaml
│   └── logging.yaml
├── src/agency_engine/
│   ├── __init__.py
│   ├── settings.py
│   ├── cli.py
│   ├── domain/
│   │   ├── models.py
│   │   ├── enums.py
│   │   ├── events.py
│   │   └── exceptions.py
│   ├── security/
│   │   ├── secret_provider.py
│   │   ├── keyring_provider.py
│   │   ├── env_provider.py
│   │   └── redaction.py
│   ├── platforms/
│   │   ├── base.py
│   │   ├── meta.py
│   │   ├── google_ads.py
│   │   ├── linkedin.py
│   │   ├── tiktok.py
│   │   └── snapchat.py
│   ├── ingestion/
│   │   ├── fetcher.py
│   │   ├── normalizer.py
│   │   ├── attribution.py
│   │   └── currency.py
│   ├── agents/
│   │   ├── contracts.py
│   │   ├── analyst.py
│   │   ├── compliance.py
│   │   ├── media_buyer.py
│   │   ├── risk.py
│   │   ├── verifier.py
│   │   └── coordinator.py
│   ├── actions/
│   │   ├── proposals.py
│   │   ├── approvals.py
│   │   ├── executor.py
│   │   ├── idempotency.py
│   │   └── rollback.py
│   ├── reporting/
│   │   ├── briefing.py
│   │   └── telegram.py
│   ├── persistence/
│   │   ├── database.py
│   │   ├── repositories.py
│   │   └── migrations/
│   ├── observability/
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   └── tracing.py
│   └── scheduler/
│       ├── jobs.py
│       └── locks.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── fixtures/
│   └── e2e/
├── scripts/
│   ├── onboard_client.py
│   ├── validate_credentials.py
│   ├── backfill_metrics.py
│   └── rotate_secrets.py
├── prompts/
│   ├── master_orchestrator.md
│   ├── analyst.md
│   ├── compliance.md
│   ├── media_buyer.md
│   └── verifier.md
└── docs/
    ├── architecture.md
    ├── runbook.md
    ├── threat-model.md
    └── platform-onboarding.md
```

### মূল data flow

```text
Scheduler/CLI
  -> Coordinator
  -> Platform adapters (read-only)
  -> Raw snapshots
  -> Normalizer
  -> Analyst Agent
  -> Compliance + Risk Agents
  -> Media Buyer proposal
  -> Verifier
  -> Approval gate
  -> Action Executor
  -> Post-action verification
  -> Audit log + Telegram briefing
```

---

## 3. Agent Design: “Swarm” নয়, Contract-Driven Workflow

Agent-দের স্বাধীন prose পাঠাতে দিলে inconsistency বাড়ে। প্রত্যেক agent structured JSON contract অনুসরণ করবে।

```python
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    platform: str
    account_id: str
    resource_id: str | None = None
    trace_id: str | None = None
    observed_at: datetime


class ProposedAction(BaseModel):
    action_id: str
    platform: str
    client_slug: str
    action: Literal["NOOP", "PAUSE", "ENABLE", "UPDATE_BUDGET"]
    resource_id: str
    old_value: Decimal | str | None = None
    new_value: Decimal | str | None = None
    reason: str
    evidence: list[Evidence]
    confidence: float = Field(ge=0, le=1)
    risk: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    requires_approval: bool = True
```

### Agent responsibilities

- **Analyst:** data quality, anomalies, normalized KPI এবং evidence তৈরি করবে। কোনো live action নেবে না।
- **Compliance:** policy rule, prohibited state, missing consent, account restriction এবং circuit breaker পরীক্ষা করবে।
- **Media Buyer:** কেবল bounded action proposal তৈরি করবে।
- **Risk Agent:** budget exposure, confidence, data freshness এবং blast radius score করবে।
- **Verifier:** proposal-এর evidence, arithmetic, current resource state এবং expected change পুনরায় যাচাই করবে।
- **Coordinator:** deterministic state machine চালাবে। Agent consensus না হলে `NOOP`।

### Consensus rule

Action execute হবে কেবল যদি:

```text
analyst.data_quality == PASS
AND compliance.status == PASS
AND risk.level in {LOW, MEDIUM}
AND verifier.status == PASS
AND proposal.confidence >= configured_threshold
AND data_age <= freshness_limit
AND approval_received == TRUE (unless explicitly allowlisted)
```

---

## 4. সবচেয়ে গুরুত্বপূর্ণ Production Fixes

### 4.1 Fake data সরানো

Telegram bot কখনো hard-coded metric ব্যবহার করবে না। Briefing service database-এর শেষ successful normalized snapshot পড়বে। Snapshot stale হলে report-এ `STALE DATA` দেখাবে, metric বানাবে না।

### 4.2 Secret management

- Local desktop: OS keyring ব্যবহার করা যায়।
- CI/server/container: managed secret store অথবা injected secret ব্যবহার করুন।
- `clients.yaml/json`-এ শুধু `secret_ref` থাকবে, token নয়।
- Log redaction বাধ্যতামূলক।
- Refresh token rotation এবং revocation runbook রাখুন।

```yaml
clients:
  global_brand:
    name: Global Brand
    timezone: Asia/Riyadh
    reporting_currency: SAR
    platforms:
      meta:
        account_id: act_123
        secret_ref: agency/global_brand/meta
        enabled: true
```

### 4.3 Resilient HTTP and rate limiting

শুধু generic retry যথেষ্ট নয়।

- Connect, read এবং total timeout আলাদা করুন।
- শুধুমাত্র transient status ও network error retry করুন।
- Exponential backoff-এর সঙ্গে jitter দিন।
- `Retry-After` ও platform headers মানুন।
- Per-platform semaphore এবং client/account-level limiter রাখুন।
- 400/401/403-এর blind retry করবেন না।
- Retry exhausted হলে dead-letter event তৈরি করুন।

```python
import asyncio
import random
import httpx


class PlatformHttpClient:
    def __init__(self, concurrency: int = 3):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=45, write=30, pool=10))

    async def request(self, method: str, url: str, **kwargs):
        for attempt in range(5):
            async with self.semaphore:
                response = await self.client.request(method, url, **kwargs)
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else min(60, 2**attempt + random.random())
            await asyncio.sleep(delay)
        raise RuntimeError("retry_exhausted")
```

### 4.4 Idempotent writes

প্রতিটি write action-এর stable fingerprint:

```text
sha256(client + platform + resource + action + intended_value + policy_version)
```

এই key database-এ unique হবে। একই action দ্বিতীয়বার execute হবে না। Execute-এর আগে বর্তমান state re-read করতে হবে। পুরোনো state বদলে গেলে proposal বাতিল।

### 4.5 Circuit breakers

Global এবং per-client policy:

```yaml
safety:
  default_mode: read_only
  max_budget_increase_percent: 10
  max_daily_spend_change_sar: 500
  max_actions_per_cycle: 3
  require_human_approval_for:
    - pause
    - enable
    - budget_increase
  block_if:
    data_stale_minutes: 180
    currency_unknown: true
    attribution_unknown: true
    active_policy_flag: true
    api_partial_failure: true
```

### 4.6 Metric normalization

Canonical schema-তে অন্তত রাখুন:

- platform, client, account, campaign, ad group, ad
- local date এবং timezone
- original currency, reporting currency এবং FX source/date
- spend, impressions, clicks, platform conversions
- conversion type
- attribution window
- source API version
- fetched_at, data_freshness, trace ID

Cross-platform CPA যোগ করার আগে conversion definition ও attribution window সমান কিনা যাচাই করুন। না হলে আলাদা দেখান।

### 4.7 Database and audit

Production-এ JSON file-এর বদলে PostgreSQL ব্যবহার করুন। Tables:

- `clients`, `platform_accounts`, `credential_refs`
- `raw_snapshots`, `normalized_metrics`
- `agent_runs`, `agent_findings`
- `action_proposals`, `approvals`, `executions`
- `audit_events`, `briefing_deliveries`

Audit event append-only হবে। Secret, raw token বা ব্যক্তিগত lead data log করা যাবে না।

### 4.8 Telegram safety

- MarkdownV2 escape বা plain text ব্যবহার করুন।
- প্রতিটি client briefing আলাদা করুন।
- Message size সীমা অতিক্রম করলে chunk করুন।
- Delivery retry ও dedup key রাখুন।
- Telegram-এ sensitive audience, lead বা token পাঠাবেন না।
- `/approve <action_id>` command চালুর আগে authorized chat allowlist এবং expiring approval token ব্যবহার করুন।

---

## 5. Antigravity-তে শুরু থেকে শেষ পর্যন্ত করানোর পরিকল্পনা

Antigravity-এর Manager surface-এ parallel agents ব্যবহার করা যায়, কিন্তু একই file একাধিক agent-কে একসঙ্গে edit করতে দেবেন না। প্রতিটি agent আলাদা branch/worktree-এ কাজ করবে।

### Phase 0: Workspace bootstrap

**Master prompt:**

```text
You are the master orchestrator for a production-grade Python 3.12 project.
First inspect the repository. Create an implementation plan and risk register.
Do not write to ad platforms. Default all connectors to read-only.
Use typed interfaces, Pydantic models, structured logs, tests, and migrations.
Never fabricate API responses or metrics. Mark unavailable integrations clearly.
Every change must include tests and a verification artifact.
```

Tasks:

1. Git initialize ও protected `main` branch।
2. `pyproject.toml`, lint, type-check, tests।
3. `.env.example`, `.gitignore`, pre-commit hooks।
4. Architecture decision records।
5. CI: lint, type-check, unit tests, secret scan।

**Exit criteria:** clean install, tests run, no secrets committed।

### Phase 1: Domain and platform contracts

Agent A: domain models ও canonical metrics।  
Agent B: platform adapter interface ও fake adapter।  
Agent C: PostgreSQL schema ও migrations।  
Agent D: threat model ও secret provider।

```python
from abc import ABC, abstractmethod


class AdsPlatform(ABC):
    @abstractmethod
    async def validate_credentials(self) -> None: ...

    @abstractmethod
    async def fetch_metrics(self, account_id, date_range): ...

    @abstractmethod
    async def preview_action(self, proposal): ...

    @abstractmethod
    async def execute_action(self, proposal, idempotency_key): ...
```

**Exit criteria:** fake adapter দিয়ে end-to-end read-only cycle চলে।

### Phase 2: Real API connectors

এক সময়ে একটি platform। প্রথমে Google Ads test account বা platform sandbox/test environment। এরপর Meta, LinkedIn, TikTok, Snapchat।

প্রতি connector-এর checklist:

- OAuth/authentication এবং token refresh
- least-privilege scopes
- API version pinning
- pagination
- rate-limit parser
- typed error mapping
- request/response trace ID
- contract tests with sanitized fixtures
- live smoke test in test account

**Exit criteria:** প্রত্যেক platform-এর credential validation এবং read-only report successful; কোনো write enabled নয়।

### Phase 3: Normalization and data quality

- Raw response immutable snapshot হিসেবে রাখুন।
- Mapper দিয়ে canonical schema তৈরি করুন।
- Duplicate, negative spend, missing currency, timezone mismatch detect করুন।
- Attribution metadata না থাকলে combined KPI block করুন।

**Exit criteria:** same fixture থেকে deterministic normalized output।

### Phase 4: Multi-agent workflow

Agent output Pydantic schema-তে validate হবে। LLM unavailable হলে deterministic rules engine read-only analysis চালাবে। Agent কখনো token বা full API response prompt-এ পাবে না।

**Exit criteria:** malformed output rejected; disagreement হলে `NOOP`; evidence ছাড়া proposal rejected।

### Phase 5: Approval and action engine

Rollout modes:

1. `READ_ONLY`
2. `SHADOW` (proposal তৈরি, execute নয়)
3. `APPROVAL_REQUIRED`
4. `LIMITED_AUTONOMY` (শুধু allowlisted low-risk action)

প্রতিটি write আগে dry-run/preview, policy check, approval, state re-read; পরে execution ও post-verification।

**Exit criteria:** duplicate action blocked; stale proposal blocked; rollback tested।

### Phase 6: Reporting and scheduling

- APScheduler একাধিক replica-তে duplicate job করতে পারে, তাই distributed lock বা single scheduler instance ব্যবহার করুন।
- Job timezone explicit রাখুন।
- Telegram report database snapshot থেকে তৈরি হবে।
- Failure summary এবং stale-data warning অন্তর্ভুক্ত করুন।

**Exit criteria:** একই briefing একবারই পাঠায়; restart-এর পর duplicate হয় না।

### Phase 7: Hardening and release

- Unit, integration, contract, e2e এবং chaos tests
- Dependency এবং secret scanning
- Backup/restore drill
- Token revocation drill
- API-deprecation monitor
- Canary client
- Incident response runbook

**Exit criteria:** staging sign-off, canary success, rollback rehearsed।

---

## 6. Antigravity Agent Task Allocation

### Master Coordinator

```text
Own the execution graph. Assign non-overlapping modules to subagents.
Require every subagent to return: changed files, tests, risks, and verification artifacts.
Never merge when tests fail, secrets are detected, or write mode is enabled by default.
```

### Connector Agent

```text
Implement one platform adapter only. Use official documentation.
Pin the API version where supported. Add pagination, token refresh, rate-limit handling,
error taxonomy, sanitized fixtures, and contract tests. Default to read-only.
```

### Security Agent

```text
Threat-model credentials, approvals, logs, webhooks, Telegram commands, and CI.
Ensure secrets are referenced, not stored. Add redaction tests and least-privilege guidance.
```

### QA Agent

```text
Attempt to break the system: duplicate jobs, expired tokens, 429 responses,
partial platform failure, stale data, currency mismatch, malformed agent JSON,
and concurrent approvals. Produce reproducible failing tests before fixes.
```

### Release Verifier

```text
Run formatter, linter, type checker, unit, integration, contract, and e2e tests.
Verify default read-only mode, migration safety, rollback, and absence of secrets.
Return PASS/FAIL with commands and artifacts. Never approve based only on prose.
```

---

## 7. Recommended Commands

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'

ruff check .
ruff format --check .
mypy src
pytest -q

python -m agency_engine.cli onboard --client global_brand
python -m agency_engine.cli credentials validate --client global_brand
python -m agency_engine.cli audit --client global_brand --mode read-only
python -m agency_engine.cli brief --client global_brand --dry-run
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

---

## 8. Testing Matrix

| স্তর | কী যাচাই করবে |
|---|---|
| Unit | metric mapper, policy rule, CPA arithmetic, redaction |
| Contract | sanitized platform response-এর schema পরিবর্তন |
| Integration | DB, secret provider, scheduler lock, Telegram mock |
| E2E | fake adapters দিয়ে full audit cycle |
| Live smoke | platform test account-এ read-only request |
| Chaos | 429, timeout, token expiry, partial outage, duplicate job |
| Security | secret scan, authorization bypass, log leakage |

যেসব critical test না পাস করলে release বন্ধ:

- secret log-এ leak হয় না
- fake/hard-coded production metric নেই
- stale data action trigger করে না
- partial API failure-এ budget write হয় না
- duplicate action একবারের বেশি execute হয় না
- unauthorized Telegram approval প্রত্যাখ্যাত হয়
- rollback বা compensating action documented এবং tested

---

## 9. Deployment Recommendation

প্রথম deployment একটি single worker + PostgreSQL দিয়ে করুন। Scale করার আগে correctness প্রমাণ করুন।

```text
Scheduler -> Queue -> Worker -> Platform APIs
                    -> PostgreSQL
                    -> Telegram
```

Environment আলাদা রাখুন:

- `dev`: fake adapters
- `staging`: test accounts, read-only
- `production`: real accounts, প্রথমে shadow mode

Deployment gates:

1. Migration dry run
2. Secret validation
3. Read-only smoke test
4. Shadow report comparison
5. Canary client
6. Human approval mode
7. Limited autonomy only after stable observation

---

## 10. Official Documentation and Version Watch

API behavior ও version বদলাতে পারে। Implementation-এর সময় নিচের official documentation-কে source of truth ধরুন:

- Google Antigravity overview: https://antigravity.google/
- Google Antigravity codelab: https://codelabs.developers.google.com/getting-started-google-antigravity
- Google Ads API introduction: https://developers.google.com/google-ads/api/docs/get-started/introduction
- Google Ads rate limits: https://developers.google.com/google-ads/api/docs/productionize/rate-limits
- Google Ads test accounts: https://developers.google.com/google-ads/api/docs/best-practices/test-accounts
- Meta Marketing API rate limiting: https://developers.facebook.com/documentation/ads-commerce/marketing-api/overview/rate-limiting.md/
- LinkedIn Marketing overview: https://learn.microsoft.com/en-us/linkedin/marketing/overview
- LinkedIn rate limiting: https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits
- TikTok Marketing API: https://business-api.tiktok.com/portal/docs/marketing-api/v2.0
- Snapchat Marketing API: https://developers.snap.com/marketing-api/home
- Snapchat authentication: https://developers.snap.com/marketing-api/Ads-API/authentication

প্রতি connector-এ `api_version`, `last_verified_at` এবং deprecation alert রাখুন।

---

## 11. Definition of Done

Project “done” বলা যাবে যখন:

- পাঁচটি platform-এর read-only connector verified
- live report-এ কোনো synthetic metric নেই
- canonical metrics ও attribution metadata সংরক্ষিত
- secrets config/repository/log-এ নেই
- retries, throttling, pagination ও token refresh tested
- all agent outputs schema-validated
- default mode read-only
- write action approval, idempotency ও post-verification সমর্থিত
- append-only audit trail আছে
- Telegram briefing deduplicated এবং stale-safe
- CI সব test ও security gate pass করে
- staging, canary ও rollback runbook verified

---

## 12. Final Recommendation

প্রকল্পটিকে “পূর্ণ autonomous swarm” হিসেবে শুরু না করে **evidence-driven, policy-governed automation platform** হিসেবে তৈরি করুন। সেরা ক্রম:

```text
Read-only data foundation
-> trusted normalization
-> explainable recommendations
-> shadow mode
-> human-approved actions
-> small allowlisted automation
```

এতে API mistake, বাজেট ক্ষতি, duplicated writes, fabricated reporting এবং policy violation-এর ঝুঁকি উল্লেখযোগ্যভাবে কমে। Antigravity-কে code generation tool হিসেবে নয়, পরিকল্পনা, parallel implementation, test generation এবং artifact-based verification-এর orchestration layer হিসেবে ব্যবহার করুন।
