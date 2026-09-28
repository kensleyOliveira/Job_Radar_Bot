import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from app.infrastructure.database.session import AsyncSessionLocal
from app.presentation.telegram.handlers import router as telegram_router
from app.infrastructure.repositories.sql_subscription_repository import SqlSubscriptionRepository
from app.infrastructure.repositories.sql_job_repository import SqlJobRepository
from app.infrastructure.scrapers.linkedin_scraper import LinkedInScraperService
from app.infrastructure.services.enrichment_service import DataEnrichmentService
from app.infrastructure.telegram.bot_service import TelegramNotificationService
from app.application.use_cases.process_radar import ProcessRadarUseCase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_background_radar():
    """Função executada periodicamente pelas tarefas do Celery Worker."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN não configurado!")
        return

    bot = Bot(token=token)
    try:
        async with AsyncSessionLocal() as session:
            sub_repo = SqlSubscriptionRepository(session)
            job_repo = SqlJobRepository(session)
            scraper = LinkedInScraperService()
            enrichment = DataEnrichmentService()
            notification = TelegramNotificationService(bot)

            use_case = ProcessRadarUseCase(sub_repo, job_repo, scraper, enrichment, notification)
            await use_case.execute()
    except Exception as e:
        logger.critical(f"Erro crítico durante a execução do radar em segundo plano: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()


async def main():
    """Entrypoint do container bot: inicia o polling contínuo do Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("ERRO FATAL: TELEGRAM_BOT_TOKEN não definido no arquivo .env!")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(telegram_router)

    logger.info("Bot iniciado com sucesso. Aguardando comandos do Telegram...")
    try:
        # Mantém o processo vivo escutando mensagens em tempo real
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())