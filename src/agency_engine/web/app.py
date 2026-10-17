"""FastAPI backend service for Omnichannel Autonomous Agency Web Dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agency_engine.actions.approvals import ApprovalManager
from agency_engine.actions.executor import ActionExecutor
from agency_engine.actions.idempotency import IdempotencyRegistry
from agency_engine.actions.rollback import RollbackEngine
from agency_engine.agents.analyst import AnalystAgent
from agency_engine.agents.coordinator import CoordinatorAgent
from agency_engine.agents.media_buyer import MediaBuyerAgent
from agency_engine.domain.enums import AutonomyMode, PlatformName
from agency_engine.domain.models import ActionProposal
from agency_engine.ingestion.fetcher import MetricFetcher
from agency_engine.persistence.database import DatabaseManager
from agency_engine.persistence.repositories import RepositoryManager
from agency_engine.platforms import get_platform_adapter
from agency_engine.reporting.briefing import BriefingService
from agency_engine.reporting.telegram import TelegramNotifier
from agency_engine.security.secret_provider import get_secret_provider
from agency_engine.settings import load_settings

app = FastAPI(title="Omnichannel Agency Engine API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
db_mgr = DatabaseManager()
idempotency_reg = IdempotencyRegistry()
approval_mgr = ApprovalManager()
executor = ActionExecutor(idempotency_registry=idempotency_reg)
rollback_eng = RollbackEngine()

# In-memory proposal and execution cache for UI responsiveness
active_proposals: dict[str, ActionProposal] = {}
execution_records: dict[str, Any] = {}


@app.on_event("startup")
async def startup() -> None:
    await db_mgr.init_models()


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    settings = load_settings()
    clients_summary = []
    for slug, c in settings.clients.items():
        clients_summary.append({
            "slug": slug,
            "name": c.name,
            "timezone": c.timezone,
            "currency": c.reporting_currency,
            "platforms": {p: pcfg.model_dump() for p, pcfg in c.platforms.items()},
        })
    return {
        "status": "online",
        "default_mode": settings.safety.default_mode,
        "max_budget_increase_percent": settings.safety.max_budget_increase_percent,
        "clients": clients_summary,
    }


class SaveCredentialsRequest(BaseModel):
    client_slug: str
    access_token: str


@app.post("/api/meta/save-credentials")
async def save_meta_credentials(req: SaveCredentialsRequest) -> dict[str, Any]:
    token = req.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Access token cannot be empty.")

    # Save to .env
    env_path = BASE_DIR / ".env"
    var_name = f"AGENCY_{req.client_slug.upper()}_META"
    lines = []
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            lines = [l for l in f.readlines() if not l.startswith(f"{var_name}=")]
    lines.append(f"{var_name}={token}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    os.environ[var_name] = token
    return {"success": True, "message": f"Token saved securely as {var_name}"}


class CreateCampaignRequest(BaseModel):
    client_slug: str = "b_fashion_explore"
    name: str
    objective: str = "OUTCOME_TRAFFIC"
    daily_budget_dollars: float = 10.0


@app.post("/api/meta/create-campaign")
async def create_meta_campaign(req: CreateCampaignRequest) -> dict[str, Any]:
    settings = load_settings()
    c = settings.clients.get(req.client_slug)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found.")

    p_meta = c.platforms.get("meta")
    if not p_meta:
        raise HTTPException(status_code=400, detail="Meta platform not configured for client.")

    secret_prov = get_secret_provider(settings.secret_provider)
    try:
        token = secret_prov.get_secret(p_meta.secret_ref)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Meta Access Token is not configured yet. Please add your token via 'Facebook Token' button.",
        ) from exc

    from agency_engine.platforms.meta import MetaPlatformAdapter

    adapter = MetaPlatformAdapter(access_token=token, client_slug=req.client_slug)
    cents = int(req.daily_budget_dollars * 100)
    try:
        res = await adapter.create_campaign(
            account_id=p_meta.account_id,
            name=req.name,
            objective=req.objective,
            daily_budget_cents=cents,
            status="PAUSED",  # Always paused initially for safety
        )
        return {"success": True, "data": res, "message": f"Campaign '{req.name}' successfully created (PAUSED for safety)!"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Meta API error: {str(exc)}") from exc



class AuditRequest(BaseModel):
    client_slug: str = "b_fashion_explore"
    mode: str = "READ_ONLY"
    use_fakes: bool = True


@app.post("/api/audit")
async def run_audit(req: AuditRequest) -> dict[str, Any]:
    settings = load_settings()
    if req.client_slug not in settings.clients:
        raise HTTPException(status_code=404, detail=f"Client '{req.client_slug}' not found.")

    c = settings.clients[req.client_slug]
    autonomy_mode = AutonomyMode(req.mode.upper().replace("-", "_"))
    secret_prov = get_secret_provider(settings.secret_provider)

    # For real client accounts without live tokens or active ads, do not generate fake data
    metrics: list[Any] = []
    p_meta = c.platforms.get("meta")
    has_token = False
    if p_meta:
        try:
            token = secret_prov.get_secret(p_meta.secret_ref)
            has_token = bool(token and token.startswith("EAA"))
        except Exception:
            has_token = False

    adapters: list[Any] = []
    if has_token:
        for p_name, p_cfg in c.platforms.items():
            if p_cfg.enabled:
                adap = get_platform_adapter(
                    platform=PlatformName(p_name),
                    client_slug=req.client_slug,
                    secret_provider=secret_prov,
                    secret_ref=p_cfg.secret_ref,
                    use_fakes=False,
                )
                adapters.append((adap, p_cfg.account_id))

        fetcher = MetricFetcher()
        ingest_res = await fetcher.fetch_all_platforms(
            adapters_with_accounts=adapters,
            target_currency=c.reporting_currency,
            timezone_str=c.timezone,
        )
        metrics = ingest_res.get("metrics", [])

    # Save to database if metrics exist
    if metrics:
        async with db_mgr.session_factory() as session:
            repo = RepositoryManager(session)
            await repo.save_metrics(metrics)


    # Multi-Agent Workflow
    analyst = AnalystAgent()
    analyst_out = await analyst.analyze(metrics)

    media_buyer = MediaBuyerAgent(max_budget_increase_percent=settings.safety.max_budget_increase_percent)
    mb_out = await media_buyer.generate_proposals(analyst_output=analyst_out, metrics=metrics)

    coordinator = CoordinatorAgent(autonomy_mode=autonomy_mode)
    decisions = []
    if adapters and mb_out.proposals:
        for prop in mb_out.proposals:
            active_proposals[prop.action_id] = prop
            adap_match = next((a for a, _ in adapters if a.platform_name == prop.platform), adapters[0][0])
            acc_id = c.platforms[prop.platform.value].account_id
            decision = await coordinator.evaluate_proposal_consensus(
                proposal=prop,
                platform_adapter=adap_match,
                account_id=acc_id,
            )
            decisions.append(decision.model_dump())

    return {
        "client": req.client_slug,
        "mode": autonomy_mode.value,
        "metrics_count": len(metrics),
        "analyst": {
            "status": analyst_out.status.value,
            "data_quality_score": analyst_out.data_quality_score,
            "anomalies": analyst_out.anomalies_detected,
        },
        "metrics": [m.model_dump() for m in metrics],
        "proposals": [p.model_dump() for p in mb_out.proposals],
        "consensus_decisions": decisions,
    }


class ApproveRequest(BaseModel):
    action_id: str
    approver: str = "Human Operator"
    client_slug: str = "b_fashion_explore"


@app.post("/api/proposals/approve")
async def approve_and_execute(req: ApproveRequest) -> dict[str, Any]:
    proposal = active_proposals.get(req.action_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Action proposal not found or expired.")

    settings = load_settings()
    c = settings.clients.get(req.client_slug)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found.")

    p_cfg = c.platforms.get(proposal.platform.value)
    account_id = p_cfg.account_id if p_cfg else "acc_default"

    secret_prov = get_secret_provider(settings.secret_provider)
    adap = get_platform_adapter(
        platform=proposal.platform,
        client_slug=req.client_slug,
        secret_provider=secret_prov,
        secret_ref=p_cfg.secret_ref if p_cfg else "ref",
        use_fakes=True,
    )

    # Approve
    approval_mgr.approve_action(proposal, approver=req.approver, channel="web_ui")

    # Execute
    exec_record = await executor.execute(proposal, adap, account_id)
    execution_records[exec_record.execution_id] = (exec_record, proposal, adap)

    return {
        "success": exec_record.state.value == "EXECUTED",
        "execution_id": exec_record.execution_id,
        "action_id": proposal.action_id,
        "fingerprint": exec_record.fingerprint,
        "state": exec_record.state.value,
        "pre_state": exec_record.pre_state_value,
        "post_state": exec_record.post_state_value,
    }


class RollbackRequest(BaseModel):
    execution_id: str


@app.post("/api/proposals/rollback")
async def rollback_execution(req: RollbackRequest) -> dict[str, Any]:
    stored = execution_records.get(req.execution_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Execution record not found.")

    exec_record, proposal, adap = stored
    success = await rollback_eng.rollback(exec_record, proposal, adap)
    return {"success": success, "execution_id": req.execution_id, "state": exec_record.state.value}


@app.get("/api/briefing")
async def get_briefing(client_slug: str = "b_fashion_explore") -> dict[str, Any]:
    settings = load_settings()
    c = settings.clients.get(client_slug)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found.")

    async with db_mgr.session_factory() as session:
        repo = RepositoryManager(session)
        metrics = await repo.get_latest_metrics(client_slug)

    service = BriefingService()
    props = list(active_proposals.values())
    text = service.generate_briefing_text(c.name, metrics, proposals=props)

    return {
        "client_name": c.name,
        "metrics_count": len(metrics),
        "raw_briefing_text": text,
    }


@app.get("/")
async def root() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)


@app.get("/connect-token.html")
async def connect_token_page() -> FileResponse:
    token_file = STATIC_DIR / "connect-token.html"
    return FileResponse(token_file)

