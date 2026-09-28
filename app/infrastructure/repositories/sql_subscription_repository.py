from datetime import datetime
from typing import List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities.subscription import SearchSubscription
from app.domain.repositories.subscription_repository import SubscriptionRepository
from app.infrastructure.database.models import SubscriptionModel

class SqlSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, subscription: SearchSubscription) -> SearchSubscription:
        model = SubscriptionModel(
            telegram_chat_id=subscription.telegram_chat_id,
            role=subscription.role,
            duration_days=subscription.duration_days,
            is_active=True,
            created_at=subscription.created_at,
            expires_at=subscription.expires_at
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        subscription.id = model.id
        return subscription

    async def get_active_subscriptions(self) -> List[SearchSubscription]:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.is_active == True,
            SubscriptionModel.expires_at >= datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [
            SearchSubscription(
                id=m.id,
                telegram_chat_id=m.telegram_chat_id,
                role=m.role,
                duration_days=m.duration_days,
                is_active=m.is_active,
                created_at=m.created_at
            )
            for m in models
        ]

    async def deactivate_expired(self) -> None:
        stmt = update(SubscriptionModel).where(
            SubscriptionModel.is_active == True,
            SubscriptionModel.expires_at < datetime.utcnow()
        ).values(is_active=False)
        await self.session.execute(stmt)
        await self.session.commit()