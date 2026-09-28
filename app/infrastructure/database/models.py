from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class SubscriptionModel(Base):
    __tablename__ = "search_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id = Column(BigInteger, nullable=False, index=True)
    role = Column(String(150), nullable=False, index=True)
    duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_hash = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(250), nullable=False)
    company_name = Column(String(250), nullable=False)
    location = Column(String(200), nullable=False)
    work_regime = Column(String(50), nullable=False)
    apply_url = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    average_salary = Column(String(100), default="Não informado")
    culture_rating = Column(Float, nullable=True)
    technical_requirements = Column(Text, default="")  
    courses_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

class NotificationLogModel(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("search_subscriptions.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('subscription_id', 'job_id', name='uq_sub_job_notification'),
    )