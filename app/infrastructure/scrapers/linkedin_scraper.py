import asyncio
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from curl_cffi import requests

from app.domain.entities.job import Job
from app.infrastructure.scrapers.tech_tags_extractor import TechTagsExtractor

logger = logging.getLogger(__name__)


class LinkedInScraperService:
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    BRAZIL_GEO_ID = "106057199"  # ID geográfico oficial do LinkedIn para o Brasil

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }

    def __init__(
        self,
        tech_tags_extractor: Optional[TechTagsExtractor] = None,
        max_concurrent_details: int = 3,
    ):
        self.tech_tags_extractor = tech_tags_extractor or TechTagsExtractor()
        self.max_concurrent_details = max_concurrent_details

    def _fetch_html_sync(self, keyword: str, location: str) -> str:
        """Executa a chamada HTTP síncrona com impersonação de TLS fixa para o Brasil."""
        params = {
            "keywords": keyword,
            "location": location,
            "geoId": self.BRAZIL_GEO_ID,
            "f_TPR": "r86400",
            "position": 1,
            "pageNum": 0,
        }
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                impersonate="chrome120",
                timeout=15,
            )
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.warning(f"Falha ao buscar listagem no LinkedIn para '{keyword}': {e}")
        return ""

    def _fetch_job_description_sync(self, external_id: str) -> str:
        """
        Consulta o endpoint público de detalhes da vaga no LinkedIn para extrair
        a descrição completa (incluindo seção de requisitos técnicos).
        """
        match = re.search(r"(\d+)$", str(external_id).strip().rstrip("/"))
        if not match:
            return ""

        job_id = match.group(1)
        url = self.JOB_DETAIL_URL.format(job_id=job_id)

        try:
            response = requests.get(
                url,
                headers=self.HEADERS,
                impersonate="chrome120",
                timeout=15,
            )
            if response.status_code != 200:
                return ""

            soup = BeautifulSoup(response.text, "lxml")
            desc_container = soup.find(
                "div", class_="show-more-less-html__markup"
            ) or soup.find("div", class_="description__text")

            if not desc_container:
                return ""

            raw_text = desc_container.get_text(separator=" ", strip=True)
            return re.sub(r"\s{2,}", " ", raw_text).strip()
        except Exception as e:
            logger.debug(f"Falha ao obter detalhes da vaga {job_id}: {e}")
            return ""

    @staticmethod
    def _is_brazilian_location(loc: str) -> bool:
        """Valida se a localização pertence ao Brasil."""
        loc_lower = loc.lower()

        # Padrões comuns de vagas estrangeiras a descartar
        non_br_terms = [
            "united states", "usa", ", us", "canada", "europe",
            "united kingdom", ", uk", "germany", "argentina", "india",
        ]
        if any(term in loc_lower for term in non_br_terms):
            return False

        # Siglas dos estados brasileiros e identificadores do país
        br_states = [
            "brasil", "brazil", "ac", "al", "ap", "am", "ba", "ce", "df",
            "es", "go", "ma", "mt", "ms", "mg", "pa", "pb", "pr", "pe",
            "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
        ]

        return any(term in loc_lower for term in br_states)

    @staticmethod
    def _detect_work_regime(text: str) -> str:
        """Identifica o regime de trabalho a partir de título, local ou descrição."""
        lower_text = text.lower()
        if any(term in lower_text for term in ("remot", "home office", "teletrabalho")):
            return "Remoto"
        if any(term in lower_text for term in ("híbrid", "hibrid")):
            return "Híbrido"
        return "Presencial"

    @classmethod
    def _parse_jobs_sync(cls, html_content: str) -> List[Job]:
        """
        Processa o parsing do HTML usando 'lxml' e filtra qualquer resultado
        fora do território brasileiro.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "lxml")
        cards = soup.find_all("li")
        jobs: List[Job] = []

        for card in cards:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            loc_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")

            if not (title_tag and company_tag and link_tag):
                continue

            title = title_tag.get_text(strip=True)
            company = company_tag.get_text(strip=True)
            loc = loc_tag.get_text(strip=True) if loc_tag else "Brasil"
            link = link_tag.get("href", "").split("?")[0].rstrip("/")

            # Filtro de segurança: descarta vagas fora do Brasil
            if not cls._is_brazilian_location(loc):
                continue

            regime = cls._detect_work_regime(f"{title} {loc}")

            job = Job(
                title=title,
                company_name=company,
                location=loc,
                work_regime=regime,
                apply_url=link,
                description=f"Oportunidade para {title} na empresa {company} ({regime}). Candidatura através do link oficial.",
                external_id=link.split("-")[-1] if "-" in link else link,
            )
            jobs.append(job)

        return jobs

    async def _populate_technical_requirements(
        self,
        job: Job,
        keyword: str,
        semaphore: asyncio.Semaphore,
        fetch_details: bool = True,
    ) -> Job:
        """
        Obtém a descrição real da vaga (quando disponível) e extrai os requisitos
        técnicos usando o TechTagsExtractor baseado no cargo pesquisado.
        """
        full_description = ""

        if fetch_details and job.external_id:
            loop = asyncio.get_running_loop()
            async with semaphore:
                full_description = await loop.run_in_executor(
                    None,
                    self._fetch_job_description_sync,
                    job.external_id,
                )

        if full_description:
            # Limita o tamanho salvo para evitar estourar o limite de 4096 chars do Telegram
            job.description = (
                full_description[:1200] + "..."
                if len(full_description) > 1200
                else full_description
            )
            # Refina o regime de trabalho caso o título/local não o tenha especificado
            if job.work_regime == "Presencial":
                job.work_regime = self._detect_work_regime(full_description)

        # Extrai requisitos técnicos combinando cargo pesquisado, título e descrição completa
        job.technical_requirements = await self.tech_tags_extractor.extract_tags(
            title=job.title,
            cargo=keyword,
            description=full_description or job.description,
        )
        return job

    async def search_jobs(
        self,
        keyword: str,
        location: str = "Brasil",
        fetch_details: bool = True,
    ) -> List[Job]:
        """
        Orquestra a pesquisa, extração assíncrona com restrição nacional
        e mapeamento dos requisitos técnicos de cada vaga.
        """
        loop = asyncio.get_running_loop()

        # 1. Baixa o HTML da listagem com geoId brasileiro
        html_content = await loop.run_in_executor(
            None,
            self._fetch_html_sync,
            keyword,
            location,
        )

        if not html_content:
            return []

        # 2. Processa o parsing dos cartões e filtra localidades brasileiras
        jobs = await loop.run_in_executor(
            None,
            self._parse_jobs_sync,
            html_content,
        )

        if not jobs:
            return []

        # 3. Coleta detalhes e popula os requisitos técnicos com concorrência controlada
        semaphore = asyncio.Semaphore(self.max_concurrent_details)
        tasks = [
            self._populate_technical_requirements(
                job=job,
                keyword=keyword,
                semaphore=semaphore,
                fetch_details=fetch_details,
            )
            for job in jobs
        ]
        enriched_jobs = await asyncio.gather(*tasks)

        return list(enriched_jobs)