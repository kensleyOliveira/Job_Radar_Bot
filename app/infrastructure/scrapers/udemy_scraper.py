import asyncio
import logging
import os
import re
import urllib.parse
from typing import List

import aiohttp
from playwright.sync_api import sync_playwright

from app.domain.entities.job import Course

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# PADRÕES DE REGEX PARA HIGIENIZAÇÃO / EXPURGO LGPD (udemy_v011.py)
# ----------------------------------------------------------------------
REGEX_TRIGGERS_NOMES = re.compile(
    r"(?i)\b(?:ministrad[oa]\s+por|apresentad[oa]\s+por|criado\s+por|com|por|pelo|pela|"
    r"prof(?:\.|essor(?:a)?)?|instrutor(?:a)?|mentor(?:a)?|taught\s+by|by)\s+"
    r"([A-ZÀ-ÖØ-ß][a-zà-öø-ÿ]+(?:\s+(?:d[aeo]s?|e)?\s*[A-ZÀ-ÖØ-ß][a-zà-öø-ÿ]+)+)",
    re.UNICODE,
)

REGEX_SUFIXOS_AUTORIA = re.compile(
    r"\s*[\-–—|]\s*(?:(?:Prof(?:\.|essor(?:a)?)?|Instrutor(?:a)?)\s+)?"
    r"([A-ZÀ-ÖØ-ß][a-zà-öø-ÿ]+(?:\s+(?:d[aeo]s?|e)?\s*[A-ZÀ-ÖØ-ß][a-zà-öø-ÿ]+)+)\s*$",
    re.UNICODE,
)


def sanitizar_texto_lgpd(texto: str) -> str:
    """
    Remove menções a nomes de pessoas físicas identificáveis e limpa
    resíduos sintáticos decorrentes do expurgo (Privacy by Design).
    """
    if not texto:
        return ""

    texto_limpo = REGEX_TRIGGERS_NOMES.sub("", texto)
    texto_limpo = REGEX_SUFIXOS_AUTORIA.sub("", texto_limpo)

    # Normalização de espaçamentos e pontuações órfãs deixadas pela remoção
    texto_limpo = re.sub(r"\s{2,}", " ", texto_limpo)
    texto_limpo = re.sub(r"\s*[\-–—|:,;]\s*$", "", texto_limpo)

    return texto_limpo.strip()


class UdemyScraper:
    def __init__(self):
        self.client_id = os.getenv("UDEMY_CLIENT_ID", "")
        self.client_secret = os.getenv("UDEMY_CLIENT_SECRET", "")

    def _scrape_playwright_sync(self, query: str, max_cursos: int = 1) -> List[Course]:
        """
        Executa a raspagem de cursos no catálogo da Udemy via Playwright Headless,
        incorporando mitigação de Cloudflare e sanitização LGPD ativa (udemy_v011.py).
        """
        cursos_coletados: List[Course] = []
        search_url = f"https://www.udemy.com/courses/search/?q={urllib.parse.quote_plus(query)}&src=ukw"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                    ignore_default_args=["--enable-automation"],
                )

                context = browser.new_context(
                    locale="pt-BR",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )

                page = context.new_page()
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                # Monitoramento de desafios WAF/Cloudflare
                for _ in range(3):
                    desafio_ativo = (
                        page.locator("text='Executando verificação de segurança'").count() > 0
                        or page.locator("text='Verificando se você não é um robô'").count() > 0
                        or "Just a moment" in page.title()
                    )
                    if desafio_ativo:
                        page.wait_for_timeout(3000)
                    else:
                        break

                seletor_card = (
                    "div.course-card-module--main-content--2XqiY, "
                    "div[class*='course-card--main-content'], "
                    "div[data-purpose='course-card']"
                )

                try:
                    page.wait_for_selector("a[href*='/course/']", timeout=12000)
                except Exception:
                    pass

                # Rolagem progressiva para disparo de lazy-loading
                page.evaluate("window.scrollBy(0, 600)")
                page.wait_for_timeout(1000)

                cards = page.locator(seletor_card).all()

                if cards:
                    for card in cards:
                        if len(cursos_coletados) >= max_cursos:
                            break
                        link_el = card.locator("h3 a, a[href*='/course/']").first
                        if link_el.count() == 0:
                            continue

                        raw_title = link_el.inner_text().strip()
                        href = link_el.get_attribute("href")
                        if not href or "/course/" not in href:
                            continue

                        url_completa = href if href.startswith("http") else f"https://www.udemy.com{href}"
                        url_limpa = url_completa.split("?")[0]

                        price_el = card.locator(
                            "div[data-purpose='course-price-text'] span:not(.ud-sr-only), "
                            "div[class*='price-text-container'] span:not(.ud-sr-only)"
                        ).first
                        price_text = price_el.inner_text().strip() if price_el.count() > 0 else ""
                        is_paid = "grátis" not in price_text.lower() and "gratuito" not in price_text.lower()

                        titulo_sanitizado = sanitizar_texto_lgpd(raw_title)

                        cursos_coletados.append(
                            Course(
                                title=titulo_sanitizado if titulo_sanitizado else raw_title,
                                url=url_limpa,
                                platform="Udemy",
                                provider_or_channel="Udemy Course",
                                is_paid=is_paid,
                            )
                        )

                # Fallback de links diretos caso os cards não venham no container esperado
                if not cursos_coletados:
                    links = page.locator(
                        "h3 a[href*='/course/'], a[data-purpose='course-card-title-link']"
                    ).all()
                    for link in links:
                        if len(cursos_coletados) >= max_cursos:
                            break
                        raw_title = link.inner_text().strip()
                        href = link.get_attribute("href")
                        if not href:
                            continue
                        url_limpa = (
                            href if href.startswith("http") else f"https://www.udemy.com{href}"
                        ).split("?")[0]

                        cursos_coletados.append(
                            Course(
                                title=sanitizar_texto_lgpd(raw_title),
                                url=url_limpa,
                                platform="Udemy",
                                provider_or_channel="Udemy Course",
                                is_paid=True,
                            )
                        )

                browser.close()

        except Exception as e:
            logger.warning(f"Raspagem Playwright da Udemy falhou para '{query}': {e}")

        # Fallback limpo caso nenhuma extração dinâmica obtenha sucesso
        if not cursos_coletados:
            cursos_coletados.append(
                Course(
                    title=f"Formação em {query.title()} na Udemy",
                    url=search_url,
                    platform="Udemy",
                    provider_or_channel="Catálogo Udemy",
                    is_paid=True,
                )
            )

        return cursos_coletados

    async def get_courses(
        self, tag: str, session: aiohttp.ClientSession, max_cursos: int = 1
    ) -> List[Course]:
        """
        Orquestra a busca na Udemy: utiliza a REST API oficial caso as chaves existam,
        ou delega para a extração do scraper Playwright com sanitização LGPD.
        """
        if self.client_id and self.client_secret:
            url = "https://www.udemy.com/api-2.0/courses/"
            params = {
                "search": tag,
                "page_size": max_cursos,
                "language": "pt",
            }
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)

            try:
                async with session.get(url, params=params, auth=auth) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        courses = []
                        for item in data.get("results", []):
                            courses.append(
                                Course(
                                    title=sanitizar_texto_lgpd(item["title"]),
                                    url=f"https://www.udemy.com{item['url']}",
                                    platform="Udemy",
                                    provider_or_channel="Udemy",
                                    is_paid=item.get("is_paid", True),
                                )
                            )
                        return courses
            except Exception as e:
                logger.error(f"Erro na chamada da API oficial Udemy: {e}")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._scrape_playwright_sync, tag, max_cursos)