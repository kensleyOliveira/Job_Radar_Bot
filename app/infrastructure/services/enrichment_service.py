import asyncio
from typing import List

import aiohttp

from app.domain.entities.job import Course, Job
from app.infrastructure.scrapers.market_culture_scraper import MarketCultureScraper
from app.infrastructure.scrapers.tech_tags_extractor import TechTagsExtractor
from app.infrastructure.scrapers.udemy_scraper import UdemyScraper
from app.infrastructure.scrapers.youtube_scraper import YouTubeScraper


class DataEnrichmentService:
    def __init__(
        self,
        udemy_scraper: UdemyScraper | None = None,
        youtube_scraper: YouTubeScraper | None = None,
        market_culture_scraper: MarketCultureScraper | None = None,
        tech_tags_extractor: TechTagsExtractor | None = None,
    ):
        self.udemy_scraper = udemy_scraper or UdemyScraper()
        self.youtube_scraper = youtube_scraper or YouTubeScraper()
        self.market_culture_scraper = market_culture_scraper or MarketCultureScraper()
        self.tech_tags_extractor = tech_tags_extractor or TechTagsExtractor()

    async def validate_tags(
        self, title: str, cargo: str | None = None, description: str = ""
    ) -> List[str]:
        """Delega a extração de tecnologias usando o dicionário dinâmico do cargo."""
        return await self.tech_tags_extractor.extract_tags(
            title=title, cargo=cargo, description=description
        )

    async def get_courses_for_tag(self, tag: str) -> List[Course]:
        """Orquestra a consulta assíncrona concorrente entre YouTube e Udemy."""
        async with aiohttp.ClientSession() as session:
            yt_task = self.youtube_scraper.get_courses(tag, session)
            udemy_task = self.udemy_scraper.get_courses(tag, session)
            yt_courses, udemy_courses = await asyncio.gather(yt_task, udemy_task)
            return yt_courses + udemy_courses

    async def enrich(self, job: Job, cargo: str | None = None) -> Job:
        # 1. Reaproveita os requisitos técnicos já extraídos pelo LinkedInScraperService
        if not getattr(job, "technical_requirements", None):
            description = getattr(job, "description", "") or ""
            job.technical_requirements = await self.validate_tags(
                title=job.title, cargo=cargo, description=description
            )

        # 2. Raspagem concorrente de remuneração e reputação de cultura
        salary_task = self.market_culture_scraper.get_salary_market(job.title)
        culture_task = self.market_culture_scraper.get_company_culture(job.company_name)

        salary, (culture_rating, _) = await asyncio.gather(salary_task, culture_task)

        job.average_salary = salary
        job.culture_rating = culture_rating

        # 3. Associação de cursos com sanitização ativa para as top 2 tags
        courses: List[Course] = []
        for tag in job.technical_requirements[:2]:
            courses.extend(await self.get_courses_for_tag(tag))

        job.courses = courses
        return job