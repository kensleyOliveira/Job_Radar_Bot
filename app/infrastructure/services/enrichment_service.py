async def validate_tags(
        self, title: str, cargo: str | None = None, description: str = ""
    ) -> List[str]:
        """Delega a extração de tecnologias usando o dicionário dinâmico do cargo."""
        return await self.tech_tags_extractor.extract_tags(
            title=title, cargo=cargo, description=description
        )

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