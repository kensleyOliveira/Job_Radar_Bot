import asyncio
import logging
import re
import urllib.parse
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MarketCultureScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def scrape_salary_market_sync(self, role: str) -> str:
        """
        Consulta salários baseados no CAGED/eSocial através do Salario.com.br.
        """
        role_cleaned = urllib.parse.quote(role.strip())
        url = f"https://www.salario.com.br/?s={role_cleaned}"

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                text_content = soup.get_text()
                matches = re.findall(r"R\$\s?[\d\.]+(?:,\d{2})?", text_content)
                if matches:
                    return f"Média de {matches[0]} / mês (Salario.com.br / CAGED)"
        except Exception as e:
            logger.debug(f"Falha ao buscar salário no Salario.com.br para '{role}': {e}")

        return "Faixa salarial não divulgada"

    def scrape_company_culture_sync(self, company_name: str) -> Tuple[Optional[float], str]:
        """
        Busca a nota de avaliação da empresa no Glassdoor via índice público DuckDuckGo.
        """
        if not company_name or company_name.lower() in ["confidencial", "empresa confidencial"]:
            return None, "Não informada"

        query = urllib.parse.quote(f"{company_name} glassdoor avaliacao nota")
        url = f"https://html.duckduckgo.com/html/?q={query}"

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                matches = re.findall(
                    r"\b([1-5][,\.][0-9])\s*(?:de 5|\/5|★|estrelas?)", res.text, re.I
                )
                if matches:
                    nota = float(matches[0].replace(",", "."))
                    if 1.0 <= nota <= 5.0:
                        return nota, "Avaliação de mercado (Web)"
        except Exception as e:
            logger.debug(f"Falha na busca indexada de cultura para '{company_name}': {e}")

        return None, "Não avaliada publicamente"

    async def get_salary_market(self, role: str) -> str:
        """Wrapper assíncrono para consulta de remuneração sem bloquear o event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scrape_salary_market_sync, role)

    async def get_company_culture(self, company_name: str) -> Tuple[Optional[float], str]:
        """Wrapper assíncrono para consulta de cultura empresarial sem bloquear o event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scrape_company_culture_sync, company_name)