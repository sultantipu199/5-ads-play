# Omnichannel Autonomous Agency Engine

Enterprise-grade, bounded-autonomy orchestration engine for Meta Ads, Google Ads, LinkedIn Ads, TikTok Ads, and Snapchat Ads.

## Key Principles
- **Read-Only by Default**: No platform mutations occur without explicit human approval.
- **Zero Fake Data**: Reports only reflect real, normalized snapshot data or explicit `STALE DATA` markers.
- **Contract-Driven Multi-Agent Swarm**: Analyst, Compliance, Media Buyer, Risk, Verifier, and Coordinator communicate strictly via Pydantic v2 schemas.
- **Idempotency & Rollback**: Every state mutation is cryptographically fingerprinted with SHA-256 and verified before/after execution.

## Quickstart
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```
