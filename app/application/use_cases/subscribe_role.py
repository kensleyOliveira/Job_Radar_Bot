import logging
from app.domain.entities.subscription import SearchSubscription
from app.domain.repositories.subscription_repository import SubscriptionRepository
from app.domain.repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


class SubscribeRoleUseCase:
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

    async def execute(self, chat_id: int, role: str, days: int) -> SearchSubscription:
        # 1. Cria a assinatura no banco
        sub = SearchSubscription(telegram_chat_id=chat_id, role=role, duration_days=days)
        saved_sub = await self.subscription_repo.create(sub)

        # 2. Faz uma varredura ao vivo no site para o novo cargo
        try:
            scraped_jobs = await self.scraper_service.search_jobs(role)
            for raw_job in scraped_jobs:
                # Se não existir no banco, enriquece e salva
                if not await self.job_repo.exists_by_hash(raw_job.job_hash):
                    enriched_job = await self.enrichment_service.enrich(raw_job)
                    await self.job_repo.save(enriched_job)
        except Exception as e:
            logger.error(f"Erro na varredura inicial para '{role}': {e}")

        # 3. Busca vagas compatíveis NUNCA enviadas a este usuário
        unnotified_jobs = await self.job_repo.get_unnotified_jobs_for_subscription(
            subscription_id=saved_sub.id,
            telegram_chat_id=chat_id,
            role=role,
            limit=10
        )

        # 4. Envia imediatamente e grava o log
        for job in unnotified_jobs:
            try:
                await self.notification_service.send_job_alert(chat_id, job)
                await self.job_repo.mark_notified(saved_sub.id, job.id)
            except Exception as notif_err:
                logger.error(f"Erro ao enviar vaga {job.id} para chat {chat_id}: {notif_err}")

        return saved_sub