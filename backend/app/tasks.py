"""Celery tasks for background PR processing and agent maintenance."""
from app.worker import celery_app
from app.pipeline.runner import run_pipeline


@celery_app.task(name="process_pr")
def process_pr_task(repo_full_name: str, pr_number: int, pr_url: str, author: str, pr_title: str = "", pr_body: str = ""):
    """Process a PR through the LangGraph pipeline."""
    import asyncio
    from app.core.database import AsyncSessionLocal
    
    async def _run():
        async with AsyncSessionLocal() as db:
            await run_pipeline(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                pr_url=pr_url,
                author=author,
                db=db,
            )
    
    asyncio.run(_run())


@celery_app.task(name="sync_all_agents")
def sync_all_agents_task():
    """Trigger ingestion for all active agents and then process pending PRs."""
    import asyncio
    import logging
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.agent import Agent
    from app.services.ingestion import ingest_agent
    
    logger = logging.getLogger(__name__)
    
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Agent).where(Agent.is_active == True)
            )
            agents = result.scalars().all()
            
            if not agents:
                return
            
            for agent in agents:
                try:
                    logger.info(f"Starting ingestion for agent {agent.id} ({agent.repo_full_name})")
                    await ingest_agent(agent.id)
                    logger.info(f"Completed ingestion for agent {agent.id}")
                except Exception as exc:
                    logger.exception(f"Ingestion failed for agent {agent.id}: {exc}")
        
        # After ingestion, trigger pending PR processing
        logger.info("Ingestion complete, triggering pending PR processing")
        process_pending_prs_task.delay()
    
    asyncio.run(_run())


@celery_app.task(name="process_pending_prs")
def process_pending_prs_task():
    """Process open PRs that existed before agent setup."""
    import asyncio
    import logging
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.agent import Agent
    from app.models.pr_event import PREvent
    from app.models.pr_processing_status import PRProcessingStatus
    from app.services.github import github_client
    
    logger = logging.getLogger(__name__)
    
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Agent).where(Agent.is_active == True)
            )
            agents = result.scalars().all()
            
            if not agents:
                logger.info("No active agents found for pending PR processing")
                return
            
            logger.info(f"Processing pending PRs for {len(agents)} agents")
            
            for agent in agents:
                try:
                    logger.info(f"Checking for open PRs in {agent.repo_full_name}")
                    prs = await github_client.list_pull_requests(agent.repo_full_name, state="open")
                    
                    if not prs:
                        logger.info(f"No open PRs found in {agent.repo_full_name}")
                        continue
                    
                    logger.info(f"Found {len(prs)} open PRs in {agent.repo_full_name}")
                    
                    for pr in prs:
                        pr_number = pr.get("number")
                        pr_url = pr.get("html_url")
                        author = pr.get("user", {}).get("login")
                        pr_title = pr.get("title", "")
                        pr_body = pr.get("body", "")
                        
                        if not pr_number or not pr_url:
                            logger.warning(f"Skipping PR with missing data: {pr}")
                            continue
                        
                        # Check if already processed
                        existing_event = await db.execute(
                            select(PREvent).where(
                                PREvent.agent_id == agent.id,
                                PREvent.pr_number == pr_number
                            )
                        )
                        if existing_event.scalar_one_or_none():
                            logger.info(f"PR #{pr_number} already processed, skipping")
                            continue
                        
                        # Create processing status entry if not exists
                        existing_status = await db.scalar(
                            select(PRProcessingStatus).where(
                                PRProcessingStatus.agent_id == agent.id,
                                PRProcessingStatus.pr_number == pr_number
                            )
                        )
                        if not existing_status:
                            processing_status = PRProcessingStatus(
                                agent_id=agent.id,
                                pr_number=pr_number,
                                pr_url=pr_url,
                                pr_title=pr_title,
                                author_github=author or "unknown",
                                status="detected",
                                detected_at=datetime.now(timezone.utc)
                            )
                            db.add(processing_status)
                            await db.commit()
                            logger.info(f"Created processing status for PR #{pr_number}")
                        
                        logger.info(f"Queueing PR #{pr_number} for processing")
                        process_pr_task.delay(
                            repo_full_name=agent.repo_full_name,
                            pr_number=pr_number,
                            pr_url=pr_url,
                            author=author or "unknown",
                            pr_title=pr_title,
                            pr_body=pr_body,
                        )
                except Exception as exc:
                    logger.exception(f"Failed to process pending PRs for agent {agent.id}: {exc}")
    
    asyncio.run(_run())


@celery_app.task(name="ensure_ollama_models")
def ensure_ollama_models_task():
    """Ensure required Ollama models are pulled."""
    import asyncio
    import httpx
    from app.core.config import settings
    
    if settings.LLM_PROVIDER != "ollama":
        return
    
    async def _run():
        models_to_check = [
            settings.OLLAMA_MODEL,
            settings.OLLAMA_EMBED_MODEL,
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models_to_check:
                try:
                    resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                    resp.raise_for_status()
                    existing_models = [m["name"] for m in resp.json().get("models", [])]
                    
                    if model not in existing_models:
                        pull_resp = await client.post(
                            f"{settings.OLLAMA_BASE_URL}/api/pull",
                            json={"name": model, "stream": False},
                            timeout=300.0,
                        )
                        pull_resp.raise_for_status()
                except Exception:
                    pass
    
    asyncio.run(_run())
