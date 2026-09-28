import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Course:
    title: str
    url: str
    platform: str 
    provider_or_channel: str
    is_paid: bool

@dataclass
class Job:
    title: str
    company_name: str
    location: str
    work_regime: str  
    apply_url: str
    description: str
    external_id: Optional[str] = None
    average_salary: Optional[str] = "Não informado"
    culture_rating: Optional[float] = None
    technical_requirements: List[str] = field(default_factory=list)
    courses: List[Course] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    job_hash: str = ""

    def __post_init__(self):
        if not self.job_hash:
            self.job_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        unique_string = f"{self.company_name.lower().strip()}_{self.title.lower().strip()}_{self.location.lower().strip()}_{self.external_id or ''}"
        return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()