import asyncio
import os
import logging
from aiogram import Bot
from app.infrastructure.database.session import AsyncSessionLocal, init_db
from app.infrastructure.repositories.sql_subscription_repository import SqlSubscriptionRepository
from app.infrastructure.repositories.sql_job_repository import SqlJobRepository
from app.infrastructure.scrapers.linkedin_scraper import LinkedInScraperService
from app.infrastructure.services.enrichment_service import DataEnrichmentService
from app.infrastructure.telegram.bot_service import TelegramNotificationService
from app.application.use_cases.process_radar import ProcessRadarUseCase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN em falta!")
        return

    # Garante a existência das tabelas na base de dados remota
    await init_db()

    bot = Bot(token=token)
    try:
        async with AsyncSessionLocal() as session:
            sub_repo = SqlSubscriptionRepository(session)
            job_repo = SqlJobRepository(session)
            scraper = LinkedInScraperService()
            enrichment = DataEnrichmentService()
            notification = TelegramNotificationService(bot)

            use_case = ProcessRadarUseCase(sub_repo, job_repo, scraper, enrichment, notification)
            logger.info("A iniciar a varredura agendada de vagas...")
            await use_case.execute()
            logger.info("Varredura e envio concluídos com sucesso!")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(run())