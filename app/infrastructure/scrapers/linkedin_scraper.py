import asyncio
from typing import List
from bs4 import BeautifulSoup
from curl_cffi import requests
from app.domain.entities.job import Job


class LinkedInScraperService:
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    BRAZIL_GEO_ID = "106057199"  # ID geográfico oficial do LinkedIn para o Brasil

    def _fetch_html_sync(self, keyword: str, location: str) -> str:
        """Executa a chamada HTTP síncrona com impersonação de TLS fixa para o Brasil."""
        params = {
            "keywords": keyword,
            "location": location,
            "geoId": self.BRAZIL_GEO_ID,  
            "f_TPR": "r86400",  
            "position": 1,
            "pageNum": 0
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                impersonate="chrome120",
                timeout=15
            )
            if response.status_code == 200:
                return response.text
        except Exception:
            pass
        return ""

    @staticmethod
    def _is_brazilian_location(loc: str) -> bool:
        """Valida se a localização pertence de facto ao Brasil."""
        loc_lower = loc.lower()
        
        # Padrões comuns de vagas estrangeiras a descartar
        non_br_terms = [
            "united states", "usa", ", us", "canada", "europe", 
            "united kingdom", ", uk", "germany", "argentina", "india"
        ]
        if any(term in loc_lower for term in non_br_terms):
            return False

        # Siglas dos estados brasileiros e identificadores de cidades
        br_states = [
            "brasil", "brazil", "ac", "al", "ap", "am", "ba", "ce", "df", 
            "es", "go", "ma", "mt", "ms", "mg", "pa", "pb", "pr", "pe", 
            "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to"
        ]
        
        # Se contiver 'brasil' ou referências a estados brasileiros
        return any(term in loc_lower for term in br_states)

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
            link = link_tag.get("href", "").split("?")[0]

            # Filtro de segurança: descarta vagas fora do Brasil
            if not cls._is_brazilian_location(loc):
                continue

            # Identificação do regime de trabalho
            regime = "Presencial"
            lower_title_loc = f"{title.lower()} {loc.lower()}"
            if "remot" in lower_title_loc or "home office" in lower_title_loc or "teletrabalho" in lower_title_loc:
                regime = "Remoto"
            elif "híbrid" in lower_title_loc or "hibrid" in lower_title_loc:
                regime = "Híbrido"

            job = Job(
                title=title,
                company_name=company,
                location=loc,
                work_regime=regime,
                apply_url=link,
                description=f"Oportunidade para {title} na empresa {company} ({regime}). Candidatura através da ligação oficial.",
                external_id=link.split("-")[-1] if "-" in link else link
            )
            jobs.append(job)

        return jobs

    async def search_jobs(self, keyword: str, location: str = "Brasil") -> List[Job]:
        """
        Orquestra a pesquisa e a extração assíncrona com restrição nacional.
        """
        loop = asyncio.get_running_loop()

        # 1. Descarrega o HTML em background com geoId brasileiro
        html_content = await loop.run_in_executor(
            None,
            self._fetch_html_sync,
            keyword,
            location
        )

        if not html_content:
            return []

        # 2. Processa o parsing e valida as localidades
        jobs = await loop.run_in_executor(
            None,
            self._parse_jobs_sync,
            html_content
        )

        return jobs