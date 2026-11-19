import html
import logging
import os
from typing import List

import aiohttp

from app.domain.entities.job import Course

logger = logging.getLogger(__name__)


class YouTubeScraper:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY", "")

    async def get_courses(
        self, tag: str, session: aiohttp.ClientSession, max_results: int = 1
    ) -> List[Course]:
        """Busca vídeos reais via YouTube Data API v3."""
        if not self.api_key:
            return [
                Course(
                    title=f"Vídeos tutoriais sobre {tag.title()}",
                    url=f"https://www.youtube.com/results?search_query=curso+{tag}",
                    platform="YouTube",
                    provider_or_channel="Busca YouTube",
                    is_paid=False,
                )
            ]

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": f"curso {tag} completo",
            "type": "video",
            "maxResults": max_results,
            "relevanceLanguage": "pt",
            "key": self.api_key,
        }

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    courses = []
                    for item in data.get("items", []):
                        courses.append(
                            Course(
                                title=html.unescape(item["snippet"]["title"]),
                                url=f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                                platform="YouTube",
                                provider_or_channel=item["snippet"]["channelTitle"],
                                is_paid=False,
                            )
                        )
                    return courses
        except Exception as e:
            logger.error(f"Erro na YouTube API: {e}")

        return []