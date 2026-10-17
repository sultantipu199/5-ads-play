# CLAUDE.md - Omnichannel Autonomous Agency Engine

## Architecture Guidelines for Claude Code CLI
This codebase implements the Omnichannel Autonomous Agency Engine for multi-platform ad campaign monitoring, analysis, and governed optimization.

### Key Tenets
1. **Bounded Autonomy**: Default to `READ_ONLY`. Write operations must satisfy consensus rules and require explicit human approval.
2. **Schema Integrity**: All agent models must derive from Pydantic v2 `BaseModel`. Reject unstructured LLM outputs.
3. **Data Quality**: Normalization across Meta, Google, LinkedIn, TikTok, and Snapchat must preserve attribution windows, original currencies, and timezone contexts.
4. **Resilience**: Every platform connector must implement:
   - Rate limit header inspection (`Retry-After`, x-rate-limit headers)
   - Exponential backoff with jitter
   - Semaphore-based concurrency throttling
   - Token refresh lifecycle management
5. **Security**: Redact tokens and credentials from logs, reports, and exception messages.

### Build and Test Commands
- Run linting: `ruff check .`
- Run formatting check: `ruff format --check .`
- Run typecheck: `mypy src`
- Run tests: `pytest -v`
