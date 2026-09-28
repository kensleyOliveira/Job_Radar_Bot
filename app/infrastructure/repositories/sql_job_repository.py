import json
import logging
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.job import Job, Course
from app.domain.repositories.job_repository import JobRepository
from app.infrastructure.database.models import JobModel, NotificationLogModel, SubscriptionModel

logger = logging.getLogger(__name__)

class SqlJobRepository(JobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: JobModel) -> Job:
        courses_raw = json.loads(model.courses_json or "[]")
        courses = [
            Course(
                title=c.get("title", ""),
                url=c.get("url", ""),
                platform=c.get("platform", ""),
                provider_or_channel=c.get("provider_or_channel", "Canal Especializado"),
                is_paid=c.get("is_paid", False),
            )
            for c in courses_raw
        ]
        
        job = Job(
            title=model.title,
            company_name=model.company_name,
            location=model.location,
            work_regime=model.work_regime,
            apply_url=model.apply_url,
            description=model.description,
            average_salary=model.average_salary,
            culture_rating=model.culture_rating,
            technical_requirements=[t for t in (model.technical_requirements or "").split(",") if t],
            courses=courses,
            created_at=model.created_at,
            job_hash=model.job_hash
        )
        job.id = model.id
        return job

    async def exists_by_hash(self, job_hash: str) -> bool:
        stmt = select(JobModel.id).where(JobModel.job_hash == job_hash).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def get_by_hash(self, job_hash: str) -> Optional[Job]:
        stmt = select(JobModel).where(JobModel.job_hash == job_hash).limit(1)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, job: Job) -> Job:
        courses_payload = json.dumps([{
            "title": c.title,
            "url": c.url,
            "platform": c.platform,
            "provider_or_channel": c.provider_or_channel,
            "is_paid": c.is_paid
        } for c in job.courses])
        
        model = JobModel(
            job_hash=job.job_hash,
            title=job.title,
            company_name=job.company_name,
            location=job.location,
            work_regime=job.work_regime,
            apply_url=job.apply_url,
            description=job.description,
            average_salary=job.average_salary,
            culture_rating=job.culture_rating,
            technical_requirements=",".join(job.technical_requirements),
            courses_json=courses_payload,
            created_at=job.created_at
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        job.id = model.id
        return job

    async def was_notified(self, subscription_id: int, job_id: int) -> bool:
        stmt = select(NotificationLogModel.id).where(
            NotificationLogModel.subscription_id == subscription_id,
            NotificationLogModel.job_id == job_id
        ).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def was_user_notified(self, chat_id: int, job_id: int) -> bool:
        stmt = (
            select(NotificationLogModel.id)
            .join(SubscriptionModel, SubscriptionModel.id == NotificationLogModel.subscription_id)
            .where(
                SubscriptionModel.telegram_chat_id == chat_id,
                NotificationLogModel.job_id == job_id
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def mark_notified(self, subscription_id: int, job_id: int) -> None:
        log = NotificationLogModel(subscription_id=subscription_id, job_id=job_id)
        self.session.add(log)
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            # Correção: Agora o erro não passa mais silenciosamente
            logger.error(f"Erro ao marcar vaga {job_id} como notificada para a inscrição {subscription_id}: {e}")
            raise

    async def get_unnotified_jobs_for_subscription(
        self, 
        subscription_id: int, 
        telegram_chat_id: int, 
        role: str, 
        limit: int = 10
    ) -> List[Job]:
        """
        Busca vagas compatíveis utilizando PostgreSQL Full Text Search (FTS).
        Delega a remoção de stopwords e análise léxica (stemming) para o banco de dados.
        """
        # 1. Subquery: IDs das vagas já enviadas
        notified_job_ids_stmt = (
            select(NotificationLogModel.job_id)
            .join(SubscriptionModel, SubscriptionModel.id == NotificationLogModel.subscription_id)
            .where(SubscriptionModel.telegram_chat_id == telegram_chat_id)
        )

        # 2. Concatena os campos onde a busca deve ocorrer (usando coalesce para evitar erros com campos nulos)
        search_document = (
            func.coalesce(JobModel.title, '') + ' ' + 
            func.coalesce(JobModel.description, '') + ' ' + 
            func.coalesce(JobModel.technical_requirements, '')
        )

        # 3. Aplica o Full Text Search do PostgreSQL
        # to_tsvector: Transforma os campos da tabela em um vetor de palavras (já otimizado)
        # plainto_tsquery: Transforma o input do usuário ('role') em uma query de busca
        # op('@@'): Operador de match do PostgreSQL
        fts_filter = func.to_tsvector('portuguese', search_document).op('@@')(
            func.plainto_tsquery('portuguese', role)
        )

        # 4. Monta a Query Final
        stmt = (
            select(JobModel)
            .where(
                JobModel.id.not_in(notified_job_ids_stmt),
                fts_filter
            )
            .order_by(JobModel.created_at.desc())
            .limit(limit)
        )

        res = await self.session.execute(stmt)
        models = res.scalars().all()
        return [self._to_entity(m) for m in models]