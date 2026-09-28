import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("job_radar_tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.beat_schedule = {
    "run-radar-every-4-hours": {
        "task": "app.infrastructure.tasks.celery_app.execute_radar_cycle",
        "schedule": 14400.0,  # a cada 4 horas
    },
}
celery_app.conf.timezone = "UTC"


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def execute_radar_cycle(self):
    """
    Executa o ciclo de radar com retentativas automáticas em caso de falha sistêmica.
    - autoretry_for: intercepta exceções não tratadas e agenda nova tentativa.
    - retry_backoff: dobra o intervalo a cada falha (60s, 120s, 240s...).
    - retry_jitter: adiciona aleatoriedade para evitar picos simultâneos no servidor.
    """
    import asyncio
    from app.main import run_background_radar

    logger.info(f"Iniciando ciclo do radar (Tentativa {self.request.retries + 1}/{self.max_retries + 1})")
    try:
        asyncio.run(run_background_radar())
    except Exception as exc:
        logger.error(f"Tentativa {self.request.retries + 1} falhou: {exc}. Agendando retentativa...")
        raise exc