# Omnichannel Autonomous Agency Engine - Agent Directives & Standards

## 1. System Mission & Scope
An enterprise-grade, bounded-autonomy ad agency orchestration engine managing:
- **Platforms**: Meta Ads, Google Ads, LinkedIn Ads, TikTok Ads, Snapchat Ads.
- **Reporting & Notifications**: Deduplicated Telegram briefings, audit logs, and anomaly detection.
- **Autonomy Progression**:
  1. `READ_ONLY` (Default & enforced until explicit human approval)
  2. `SHADOW` (Proposals generated, simulation/dry-run only)
  3. `APPROVAL_REQUIRED` (Human operator approval needed via CLI or verified Telegram command)
  4. `LIMITED_AUTONOMY` (Allowlisted, low-risk, reversible actions with strict budget caps)

## 2. Immutable Operational Rules
- **Zero Fake Data**: Never use hardcoded or synthetic metrics in production reports. If an API fails or data is stale, explicitly flag `STALE DATA` or `DATA UNAVAILABLE`.
- **Zero Secrets in Code/Logs**: Secrets reside in secure providers (Keyring, Vault, or environment variables). Never commit tokens or credentials. All logs must sanitize and redact sensitive values.
- **Contract-Driven Agents**: Every agent interaction uses strict Pydantic v2 schemas. Free-form text prompts are strictly validated against JSON contracts.
- **Idempotency & Reversibility**: Every write action requires a cryptographic fingerprint (`sha256(client + platform + resource + action + intended_value + policy_version)`), pre-execution state re-reading, and a defined rollback strategy.
- **Consensus Before Action**: Actions execute only when Analyst, Compliance, Risk, and Verifier reach unanimous validation according to configured thresholds.

## 3. Technology Stack & Coding Conventions
- **Language**: Python 3.12+ (Type hints required everywhere)
- **Validation**: Pydantic v2
- **HTTP Client**: `httpx` (with async concurrency control, jittered exponential backoff, rate limit header parsing)
- **Logging**: `structlog` with automated secret redaction
- **Database & Persistence**: SQLAlchemy (Async) / Alembic / PostgreSQL (SQLite fallback for hermetic local testing)
- **Testing**: `pytest`, `pytest-asyncio`, with comprehensive unit, contract, integration, and chaos test suites.
- **Quality Gates**: `ruff check`, `ruff format --check`, `mypy --strict`.
