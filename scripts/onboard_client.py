"""Interactive onboarding utility for connecting real client ad accounts."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import click
import yaml

from agency_engine.domain.enums import PlatformName
from agency_engine.platforms.meta import MetaPlatformAdapter
from agency_engine.security.secret_provider import EnvSecretProvider


@click.command()
@click.option("--client-slug", prompt="Client ID / Slug (e.g. my_brand)", help="Unique slug for the client")
@click.option("--client-name", prompt="Client Display Name", help="Human-readable business name")
@click.option("--timezone", prompt="Timezone", default="Asia/Dhaka", help="Client local timezone")
@click.option("--currency", prompt="Reporting Currency (e.g. USD, BDT, SAR)", default="USD", help="Currency")
@click.option("--ad-account-id", prompt="Meta Ad Account ID (e.g. act_1234567890)", help="Ad Account ID")
@click.option(
    "--access-token", prompt="Meta Access Token (EAAB...)", hide_input=True, help="Meta User or System User Token"
)
def onboard_meta(
    client_slug: str,
    client_name: str,
    timezone: str,
    currency: str,
    ad_account_id: str,
    access_token: str,
) -> None:
    """Connect a real Facebook (Meta) Ad Account to the Autonomous Engine."""
    base_dir = Path(__file__).resolve().parent.parent
    config_dir = base_dir / "config"
    clients_path = config_dir / "clients.yaml"

    clean_slug = client_slug.lower().strip().replace(" ", "_")
    clean_account = ad_account_id.strip()
    if not clean_account.startswith("act_"):
        clean_account = f"act_{clean_account}"

    click.echo("\n[1/3] Validating Meta Access Token with Graph API...")

    async def _test() -> bool:
        adapter = MetaPlatformAdapter(access_token=access_token.strip(), client_slug=clean_slug)
        try:
            return await adapter.validate_credentials()
        except Exception as exc:
            click.echo(f"  [!] Validation error: {exc}")
            return False

    is_valid = asyncio.run(_test())
    if not is_valid:
        click.echo("  [!] Failed to validate Meta token. Please verify token permissions (ads_read, ads_management).")
        return

    click.echo("  [+] Token verified successfully with Meta Graph API!")

    # 2. Save secret into .env safely
    click.echo("\n[2/3] Securely storing token reference...")
    env_path = base_dir / ".env"
    secret_var_name = f"AGENCY_{clean_slug.upper()}_META"

    # Read existing .env or create
    existing_lines = []
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            existing_lines = f.readlines()

    # Filter out existing var
    filtered_lines = [l for l in existing_lines if not l.startswith(f"{secret_var_name}=")]
    filtered_lines.append(f"{secret_var_name}={access_token.strip()}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(filtered_lines)

    click.echo(f"  [+] Secret registered in .env as {secret_var_name}")

    # 3. Update config/clients.yaml
    click.echo("\n[3/3] Updating config/clients.yaml...")
    clients_data = {"clients": {}}
    if clients_path.exists():
        with open(clients_path, encoding="utf-8") as f:
            clients_data = yaml.safe_load(f) or {"clients": {}}

    clients_data["clients"][clean_slug] = {
        "name": client_name,
        "timezone": timezone,
        "reporting_currency": currency.upper(),
        "platforms": {
            "meta": {
                "account_id": clean_account,
                "secret_ref": f"agency/{clean_slug}/meta",
                "enabled": True,
            }
        },
    }

    with open(clients_path, "w", encoding="utf-8") as f:
        yaml.dump(clients_data, f, sort_keys=False)

    click.echo(f"  [+] Client '{clean_slug}' successfully onboarded in config/clients.yaml!")
    click.echo("\n" + "=" * 60)
    click.echo("Ready to run! Next commands:")
    click.echo(f"  1. Live Audit (Read-Only):")
    click.echo(f"     python -m agency_engine.cli audit --client {clean_slug} --mode read_only")
    click.echo(f"  2. Live Executive Briefing:")
    click.echo(f"     python -m agency_engine.cli brief --client {clean_slug} --dry-run")
    click.echo("=" * 60 + "\n")


if __name__ == "__main__":
    onboard_meta()
