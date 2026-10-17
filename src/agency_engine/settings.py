"""Engine settings and global configuration loader."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SafetyPolicy(BaseModel):
    default_mode: str = "READ_ONLY"
    max_budget_increase_percent: float = 10.0
    max_daily_spend_change_sar: float = 500.0
    max_actions_per_cycle: int = 3
    freshness_limit_minutes: int = 180
    confidence_threshold: float = 0.85
    require_human_approval_for: list[str] = Field(default_factory=lambda: ["PAUSE", "ENABLE", "UPDATE_BUDGET"])
    block_if_data_stale: bool = True
    block_if_currency_unknown: bool = True
    block_if_attribution_unknown: bool = True
    block_if_partial_failure: bool = True


class PlatformConfig(BaseModel):
    account_id: str
    secret_ref: str
    enabled: bool = True


class ClientConfig(BaseModel):
    name: str
    timezone: str = "UTC"
    reporting_currency: str = "USD"
    platforms: dict[str, PlatformConfig] = Field(default_factory=dict)


class Settings(BaseModel):
    app_env: str = "development"
    log_level: str = "INFO"
    secret_provider: str = "env"
    database_url: str = "sqlite+aiosqlite:///agency_engine.db"
    telegram_bot_token: str | None = None
    telegram_default_chat_id: str | None = None
    telegram_approval_allowlist: list[str] = Field(default_factory=list)
    safety: SafetyPolicy = Field(default_factory=SafetyPolicy)
    clients: dict[str, ClientConfig] = Field(default_factory=dict)


def load_settings(base_dir: Path | None = None) -> Settings:
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent.parent

    # Auto-load .env file into os.environ
    env_file = base_dir / ".env"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                sline = line.strip()
                if sline and not sline.startswith("#") and "=" in sline:
                    k, v = sline.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ or not os.environ[k]:
                        os.environ[k] = v

    config_dir = base_dir / "config"
    safety = SafetyPolicy()
    clients: dict[str, ClientConfig] = {}

    policies_path = config_dir / "policies.yaml"
    if policies_path.exists():
        with open(policies_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            raw_safety = data.get("safety", {})
            cb = raw_safety.get("circuit_breakers", {})
            safety = SafetyPolicy(
                default_mode=raw_safety.get("default_mode", "READ_ONLY"),
                max_budget_increase_percent=float(raw_safety.get("max_budget_increase_percent", 10.0)),
                max_daily_spend_change_sar=float(raw_safety.get("max_daily_spend_change_sar", 500.0)),
                max_actions_per_cycle=int(raw_safety.get("max_actions_per_cycle", 3)),
                freshness_limit_minutes=int(raw_safety.get("freshness_limit_minutes", 180)),
                confidence_threshold=float(raw_safety.get("confidence_threshold", 0.85)),
                require_human_approval_for=raw_safety.get(
                    "require_human_approval_for", ["PAUSE", "ENABLE", "UPDATE_BUDGET"]
                ),
                block_if_data_stale=cb.get("block_if_data_stale", True),
                block_if_currency_unknown=cb.get("block_if_currency_unknown", True),
                block_if_attribution_unknown=cb.get("block_if_attribution_unknown", True),
                block_if_partial_failure=cb.get("block_if_partial_failure", True),
            )

    clients_path = config_dir / "clients.yaml"
    if not clients_path.exists():
        clients_path = config_dir / "clients.example.yaml"
    if clients_path.exists():
        with open(clients_path, encoding="utf-8") as f:
            cdata = yaml.safe_load(f) or {}
            for slug, cinfo in cdata.get("clients", {}).items():
                platforms_map: dict[str, PlatformConfig] = {}
                for p_name, p_data in cinfo.get("platforms", {}).items():
                    platforms_map[p_name] = PlatformConfig(
                        account_id=str(p_data.get("account_id")),
                        secret_ref=str(p_data.get("secret_ref")),
                        enabled=bool(p_data.get("enabled", True)),
                    )
                clients[slug] = ClientConfig(
                    name=cinfo.get("name", slug),
                    timezone=cinfo.get("timezone", "UTC"),
                    reporting_currency=cinfo.get("reporting_currency", "USD"),
                    platforms=platforms_map,
                )

    allowlist_raw = os.getenv("TELEGRAM_APPROVAL_ALLOWLIST", "")
    allowlist = [x.strip() for x in allowlist_raw.split(",") if x.strip()]

    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        secret_provider=os.getenv("SECRET_PROVIDER", "env"),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///agency_engine.db"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_default_chat_id=os.getenv("TELEGRAM_DEFAULT_CHAT_ID"),
        telegram_approval_allowlist=allowlist,
        safety=safety,
        clients=clients,
    )
