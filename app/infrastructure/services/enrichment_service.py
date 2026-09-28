import asyncio
import html
import json
import logging
import os
import re
import urllib.parse
from typing import List, Optional, Tuple

import aiohttp
import requests
from bs4 import BeautifulSoup

from app.domain.entities.job import Job, Course

logger = logging.getLogger(__name__)

# Configurações de API (Carregue do seu .env)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
UDEMY_CLIENT_ID = os.getenv("UDEMY_CLIENT_ID", "")
UDEMY_CLIENT_SECRET = os.getenv("UDEMY_CLIENT_SECRET", "")


class DataEnrichmentService:
    def __init__(self):
        # Headers padronizados e mais simples (Salario.com.br não exige evasão pesada)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _scrape_salary_market_sync(self, role: str) -> str:
        """
        Consulta salários baseados no CAGED/eSocial através do Salario.com.br.
        Muito mais estável, sem bloqueios de Cloudflare/DataDome.
        """
        role_cleaned = urllib.parse.quote(role.strip())
        url = f"https://www.salario.com.br/?s={role_cleaned}"

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Procura a tag principal de salário da pesquisa
                # O site costuma trazer: "Um [Cargo] ganha em média R$ 5.000,00..."
                text_content = soup.get_text()
                
                # Regex para encontrar o primeiro valor em Reais que aparece no texto útil
                matches = re.findall(r"R\$\s?[\d\.]+(?:,\d{2})?", text_content)
                if matches:
                    return f"Média de {matches[0]} / mês (Salario.com.br / CAGED)"

        except Exception as e:
            logger.debug(f"Falha ao buscar salário no Salario.com.br para '{role}': {e}")

        return "Faixa salarial não divulgada"

    def _scrape_company_culture_sync(self, company_name: str) -> Tuple[Optional[float], str]:
        """
        Mantido o fallback via DuckDuckGo para encontrar a nota, 
        pois acessar o Glassdoor diretamente está bloqueado.
        """
        if not company_name or company_name.lower() in ["confidencial", "empresa confidencial"]:
            return None, "Não informada"

        query = urllib.parse.quote(f"{company_name} glassdoor avaliacao nota")
        url = f"https://html.duckduckgo.com/html/?q={query}"

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                matches = re.findall(r"\b([1-5][,\.][0-9])\s*(?:de 5|\/5|★|estrelas?)", res.text, re.I)
                if matches:
                    nota = float(matches[0].replace(",", "."))
                    if 1.0 <= nota <= 5.0:
                        return nota, "Avaliação de mercado (Web)"
        except Exception as e:
            logger.debug(f"Falha na busca indexada de cultura para '{company_name}': {e}")

        return None, "Não avaliada publicamente"

    async def validate_tags(self, title: str) -> List[str]:
        """Extrai as tecnologias essenciais mencionadas no cargo."""
        tech_dictionary = [
            "python", "java", "c#", "c++", "golang", "ruby", "php", "javascript",
            "typescript", "react", "angular", "vue", "node", "fastapi", "django",
            "spring", "sql", "postgresql", "mysql", "mongodb", "aws", "azure",
            "gcp", "docker", "kubernetes", "devops", "spark", "hadoop"
        ]
        title_clean = title.lower()
        matched = [t for t in tech_dictionary if t in title_clean]
        return matched if matched else ["desenvolvimento", "tecnologia"]

    async def _get_youtube_courses(self, tag: str, session: aiohttp.ClientSession) -> List[Course]:
        """Busca vídeos reais via YouTube Data API v3."""
        if not YOUTUBE_API_KEY:
            # Fallback se a API Key não estiver configurada
            return [Course(
                title=f"Vídeos tutoriais sobre {tag.title()}",
                url=f"https://www.youtube.com/results?search_query=curso+{tag}",
                platform="YouTube",
                provider_or_channel="Busca YouTube",
                is_paid=False
            )]

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": f"curso {tag} completo",
            "type": "video",
            "maxResults": 1,
            "relevanceLanguage": "pt",
            "key": YOUTUBE_API_KEY
        }
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    courses = []
                    for item in data.get("items", []):
                        courses.append(Course(
                            title=html.unescape(item["snippet"]["title"]),
                            url=f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                            platform="YouTube",
                            provider_or_channel=item["snippet"]["channelTitle"],
                            is_paid=False
                        ))
                    return courses
        except Exception as e:
            logger.error(f"Erro na YouTube API: {e}")
            
        return []

    async def _get_udemy_courses(self, tag: str, session: aiohttp.ClientSession) -> List[Course]:
        """Busca cursos via Udemy REST API Oficial."""
        if not UDEMY_CLIENT_ID or not UDEMY_CLIENT_SECRET:
            # Fallback se a API não estiver configurada
            return [Course(
                title=f"Cursos de {tag.title()} na Udemy",
                url=f"https://www.udemy.com/courses/search/?q={tag}",
                platform="Udemy",
                provider_or_channel="Busca Udemy",
                is_paid=True
            )]

        url = "https://www.udemy.com/api-2.0/courses/"
        params = {
            "search": tag,
            "page_size": 1,
            "language": "pt"
        }
        auth = aiohttp.BasicAuth(UDEMY_CLIENT_ID, UDEMY_CLIENT_SECRET)
        
        try:
            async with session.get(url, params=params, auth=auth) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    courses = []
                    for item in data.get("results", []):
                        # Pega o nome do instrutor (se disponível)
                        instructors = item.get("visible_instructors", [{"title": "Instrutor Udemy"}])
                        provider = instructors[0]["title"] if instructors else "Udemy"
                        
                        courses.append(Course(
                            title=item["title"],
                            url=f"https://www.udemy.com{item['url']}",
                            platform="Udemy",
                            provider_or_channel=provider,
                            is_paid=item.get("is_paid", True)
                        ))
                    return courses
        except Exception as e:
            logger.error(f"Erro na Udemy API: {e}")
            
        return []

    async def get_courses_for_tag(self, tag: str) -> List[Course]:
        """Orquestra as buscas nas APIs de cursos de forma concorrente."""
        async with aiohttp.ClientSession() as session:
            yt_task = self._get_youtube_courses(tag, session)
            udemy_task = self._get_udemy_courses(tag, session)
            
            # Aguarda ambas as APIs responderem simultaneamente
            yt_courses, udemy_courses = await asyncio.gather(yt_task, udemy_task)
            
            return yt_courses + udemy_courses

    async def enrich(self, job: Job) -> Job:
        loop = asyncio.get_running_loop()

        # 1. Extração de tags técnicas
        job.technical_requirements = await self.validate_tags(job.title)

        # 2. Raspagem de Salário (Salario.com.br) e Cultura (Thread Pools)
        salary_task = loop.run_in_executor(None, self._scrape_salary_market_sync, job.title)
        culture_task = loop.run_in_executor(None, self._scrape_company_culture_sync, job.company_name)

        salary, (culture_rating, _) = await asyncio.gather(salary_task, culture_task)

        job.average_salary = salary
        job.culture_rating = culture_rating

        # 3. Associação dos cursos via APIs (YouTube e Udemy)
        courses = []
        for tag in job.technical_requirements[:2]: # Limita a 2 tags para não gerar muito tráfego/custo
            courses.extend(await self.get_courses_for_tag(tag))

        job.courses = courses
        return job