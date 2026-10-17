"""Enterprise CLI interface for agency orchestration."""

from __future__ import annotations

import asyncio
import sys

import click
import structlog

from agency_engine.agents.analyst import AnalystAgent
from agency_engine.agents.coordinator import CoordinatorAgent
from agency_engine.agents.media_buyer import MediaBuyerAgent
from agency_engine.domain.enums import AutonomyMode, PlatformName
from agency_engine.ingestion.fetcher import MetricFetcher
from agency_engine.persistence.database import DatabaseManager
from agency_engine.persistence.repositories import RepositoryManager
from agency_engine.platforms import get_platform_adapter
from agency_engine.reporting.briefing import BriefingService
from agency_engine.reporting.telegram import TelegramNotifier
from agency_engine.security.secret_provider import get_secret_provider
from agency_engine.settings import load_settings

logger = structlog.get_logger()

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        reconf_out = getattr(sys.stdout, "reconfigure", None)
        if callable(reconf_out):
            reconf_out(encoding="utf-8")
        reconf_err = getattr(sys.stderr, "reconfigure", None)
        if callable(reconf_err):
            reconf_err(encoding="utf-8")
    except Exception:
        pass


@click.group()
def cli() -> None:
    """Omnichannel Autonomous Agency Engine CLI."""


@cli.command("onboard")
@click.option("--client", required=True, help="Client slug to onboard")
def onboard_client(client: str) -> None:
    """Verify or bootstrap client configuration."""
    settings = load_settings()
    if client in settings.clients:
        c = settings.clients[client]
        click.echo(f"Client '{client}' already registered: {c.name} ({c.reporting_currency}, {c.timezone})")
        click.echo(f"Configured platforms: {list(c.platforms.keys())}")
    else:
        click.echo(f"Client '{client}' not found in config/clients.yaml.")
        click.echo("Please add entry to config/clients.yaml before proceeding.")


@cli.command("credentials")
@click.argument("action", type=click.Choice(["validate"]))
@click.option("--client", required=True, help="Client slug")
def manage_credentials(action: str, client: str) -> None:
    """Validate client API credentials and scopes."""
    settings = load_settings()
    if client not in settings.clients:
        click.echo(f"Client '{client}' not found.")
        sys.exit(1)

    c = settings.clients[client]
    secret_prov = get_secret_provider(settings.secret_provider)
    click.echo(f"Validating credentials for client '{client}' across {len(c.platforms)} platform(s)...")

    async def _run() -> None:
        for p_name, p_cfg in c.platforms.items():
            if not p_cfg.enabled:
                click.echo(f"  [-] [{p_name.upper()}]: DISABLED (Skipping)")
                continue
            adapter = get_platform_adapter(
                platform=PlatformName(p_name),
                client_slug=client,
                secret_provider=secret_prov,
                secret_ref=p_cfg.secret_ref,
                use_fakes=True,  # Default to hermetic validation
            )
            try:
                valid = await adapter.validate_credentials()
                status = "PASSED" if valid else "FAILED"
                click.echo(f"  [+] [{p_name.upper()}]: {status}")
            except Exception as exc:
                click.echo(f"  [!] [{p_name.upper()}]: FAILED ({exc})")

    asyncio.run(_run())


@cli.command("audit")
@click.option("--client", required=True, help="Client slug")
@click.option(
    "--mode",
    default="read_only",
    help="Engine autonomy mode: read_only, shadow, approval_required, limited_autonomy",
)
def run_audit(client: str, mode: str) -> None:
    """Run full audit cycle: ingestion, multi-agent consensus, and proposal generation."""
    settings = load_settings()
    if client not in settings.clients:
        click.echo(f"Client '{client}' not found.")
        sys.exit(1)

    c = settings.clients[client]
    clean_mode = mode.upper().replace("-", "_")
    autonomy_mode = AutonomyMode(clean_mode)

    secret_prov = get_secret_provider(settings.secret_provider)
    db = DatabaseManager(settings.database_url)

    click.echo(f"Starting audit cycle for '{c.name}' in {autonomy_mode.value} mode...")

    async def _audit() -> None:
        await db.init_models()
        adapters = []
        for p_name, p_cfg in c.platforms.items():
            if p_cfg.enabled:
                adap = get_platform_adapter(
                    platform=PlatformName(p_name),
                    client_slug=client,
                    secret_provider=secret_prov,
                    secret_ref=p_cfg.secret_ref,
                    use_fakes=True,
                )
                adapters.append((adap, p_cfg.account_id))

        fetcher = MetricFetcher()
        ingest_res = await fetcher.fetch_all_platforms(
            adapters_with_accounts=adapters,
            target_currency=c.reporting_currency,
            timezone_str=c.timezone,
        )

        metrics = ingest_res["metrics"]
        click.echo(f"Ingested {len(metrics)} canonical metrics across {len(adapters)} platform(s).")

        # Persist metrics
        async with db.session_factory() as session:
            repo = RepositoryManager(session)
            await repo.save_metrics(metrics)

        # Multi-Agent Workflow
        analyst = AnalystAgent()
        analyst_out = await analyst.analyze(metrics)
        click.echo(
            f"Analyst Status: {analyst_out.status.value} (Data Quality: {analyst_out.data_quality_score * 100:.0f}%)"
        )
        if analyst_out.anomalies_detected:
            click.echo("Anomalies Detected:")
            for an in analyst_out.anomalies_detected:
                click.echo(f"  [!] {an}")

        media_buyer = MediaBuyerAgent(max_budget_increase_percent=settings.safety.max_budget_increase_percent)
        mb_out = await media_buyer.generate_proposals(analyst_output=analyst_out, metrics=metrics)

        coordinator = CoordinatorAgent(autonomy_mode=autonomy_mode)
        for prop in mb_out.proposals:
            click.echo(f"\nEvaluating Proposal: {prop.action.value} on {prop.resource_name} ({prop.resource_id})")
            # Find adapter
            adap_match = next((a for a, _ in adapters if a.platform_name == prop.platform), adapters[0][0])
            acc_id = c.platforms[prop.platform.value].account_id
            decision = await coordinator.evaluate_proposal_consensus(
                proposal=prop,
                platform_adapter=adap_match,
                account_id=acc_id,
            )
            click.echo(f"  Decision Approved: {decision.approved}")
            click.echo(f"  Execution Permitted: {decision.execution_permitted}")
            if decision.block_reasons:
                click.echo(f"  Guards Triggered: {', '.join(decision.block_reasons)}")

        await db.close()

    asyncio.run(_audit())


@cli.command("brief")
@click.option("--client", required=True, help="Client slug")
@click.option("--dry-run", is_flag=True, default=False, help="Print to console without sending to Telegram")
def generate_brief(client: str, dry_run: bool) -> None:
    """Generate and deliver daily executive briefing."""
    settings = load_settings()
    if client not in settings.clients:
        click.echo(f"Client '{client}' not found.")
        sys.exit(1)

    c = settings.clients[client]
    db = DatabaseManager(settings.database_url)

    async def _brief() -> None:
        await db.init_models()
        async with db.session_factory() as session:
            repo = RepositoryManager(session)
            metrics = await repo.get_latest_metrics(client)

        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            default_chat_id=settings.telegram_default_chat_id,
            dry_run=dry_run,
        )
        service = BriefingService(notifier=notifier)
        text = service.generate_briefing_text(c.name, metrics)
        click.echo("\n--- EXECUTIVE BRIEFING OUTPUT ---")
        click.echo(text)
        click.echo("---------------------------------\n")

        if not dry_run and settings.telegram_bot_token:
            sent = await service.deliver_briefing(c.name, client, metrics)
            click.echo(f"Dispatched to Telegram: {sent}")
        else:
            click.echo("Dry-run mode: Briefing generated and verified without network dispatch.")

        await db.close()

    asyncio.run(_brief())


if __name__ == "__main__":
    cli()
