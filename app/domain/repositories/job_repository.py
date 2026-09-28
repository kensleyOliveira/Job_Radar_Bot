from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.job import Job

class JobRepository(ABC):
    @abstractmethod
    async def exists_by_hash(self, job_hash: str) -> bool:
        pass

    @abstractmethod
    async def get_by_hash(self, job_hash: str) -> Optional[Job]:
        pass

    @abstractmethod
    async def save(self, job: Job) -> Job:
        pass

    @abstractmethod
    async def was_notified(self, subscription_id: int, job_id: int) -> bool:
        pass

    @abstractmethod
    async def mark_notified(self, subscription_id: int, job_id: int) -> None:
        pass

    @abstractmethod
    async def get_unnotified_jobs_for_subscription(self, subscription_id: int, role: str, limit: int = 10) -> List[Job]:
        pass

    @abstractmethod
    async def get_unnotified_jobs_for_subscription(
        self, 
        subscription_id: int, 
        telegram_chat_id: int, 
        role: str, 
        limit: int = 10
    ) -> List[Job]:
        pass