from abc import ABC, abstractmethod
from typing import List
from app.domain.entities.subscription import SearchSubscription

class SubscriptionRepository(ABC):
    @abstractmethod
    async def create(self, subscription: SearchSubscription) -> SearchSubscription:
        pass

    @abstractmethod
    async def get_active_subscriptions(self) -> List[SearchSubscription]:
        pass

    @abstractmethod
    async def deactivate_expired(self) -> None:
        pass