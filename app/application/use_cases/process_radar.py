import logging
from typing import List
from app.domain.entities.job import Job
from app.domain.repositories.job_repository import JobRepository
from app.domain.repositories.subscription_repository import SubscriptionRepository

logger = logging.getLogger(__name__)


class ProcessRadarUseCase:
    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        job_repo: JobRepository,
        scraper_service,
        enrichment_service,
        notification_service,
    ):
        self.subscription_repo = subscription_repo
        self.job_repo = job_repo
        self.scraper_service = scraper_service
        self.enrichment_service = enrichment_service
        self.notification_service = notification_service

    async def execute(self):
        try:
            await self.subscription_repo.deactivate_expired()
            active_subs = await self.subscription_repo.get_active_subscriptions()
        except Exception as e:
            logger.error(f"Erro ao buscar assinaturas ativas no banco: {e}", exc_info=True)
            raise  

        logger.info(f"Processando radar para {len(active_subs)} assinaturas ativas.")
        if not active_subs:
            return

        role_map = {}
        for sub in active_subs:
            role_map.setdefault(sub.role.lower().strip(), []).append(sub)

        for role, subs in role_map.items():
            try:
                scraped_jobs = await self.scraper_service.search_jobs(role)
                if not scraped_jobs:
                    logger.info(f"Nenhuma vaga retornada para o cargo: '{role}'.")
                    continue

                # Dentro do laço de process_radar.py:
                for raw_job in scraped_jobs:
                    # 1. Recupera ou Salva a vaga no banco
                    existing_job = await self.job_repo.get_by_hash(raw_job.job_hash)
                    if existing_job:
                        target_job = existing_job
                    else:
                        enriched_job = await self.enrichment_service.enrich(raw_job)
                        target_job = await self.job_repo.save(enriched_job)

                    # 2. Notifica cada assinante individualmente se ele ainda não recebeu
                    for sub in subs: 
                        if not await self.job_repo.was_user_notified(sub.telegram_chat_id, target_job.id):
                            await self.notification_service.send_job_alert(sub.telegram_chat_id, target_job)
                            await self.job_repo.mark_notified(sub.id, target_job.id)

            except Exception as role_err:
                logger.error(f"Falha transitória ao buscar vagas para o cargo '{role}': {role_err}", exc_info=True)
                continue