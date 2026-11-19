import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class TechTagsExtractor:
    COLUNA_CARGO = "Role"

    COLUNAS_ALVO: Dict[str, str] = {
        "Linguagens": "LanguagesHaveWorkedWith",
        "Nuvem / Plataformas": "CloudPlatHaveWorkedWith",
        "SecOps & Infra": "SecOpsHaveWorkedWith",
        "Bancos de Dados": "DatabasesHaveWorkedWith",
        "Frameworks Web": "WebFrameworkHaveWorkedWith",
        "IDEs & Editores": "DevIDEHaveWorkedWith",
        "Testes de Código": "CodeTestHaveWorkedWith",
        "LLMs / IA": "LLMHaveWorkedWith",
    }

    # Mapeamento auxiliar para traduzir termos comuns em português para os cargos do CSV (inglês)
    ROLE_ALIASES: Dict[str, str] = {
        "backend": "back-end",
        "back-end": "back-end",
        "back end": "back-end",
        "frontend": "front-end",
        "front-end": "front-end",
        "front end": "front-end",
        "fullstack": "full-stack",
        "full-stack": "full-stack",
        "full stack": "full-stack",
        "ciencia de dados": "data scientist",
        "ciência de dados": "data scientist",
        "cientista de dados": "data scientist",
        "engenheiro de dados": "data engineer",
        "analista de dados": "data",
        "dados": "data",
        "devops": "devops",
        "sre": "site reliability",
        "nuvem": "cloud",
        "mobile": "mobile",
        "android": "mobile",
        "ios": "mobile",
        "qa": "qa",
        "qualidade": "qa",
        "testes": "qa",
        "seguranca": "security",
        "segurança": "security",
        "ia": "ai",
        "inteligencia artificial": "ai",
        "inteligência artificial": "ai",
        "machine learning": "machine learning",
    }

    def __init__(self, csv_path: Optional[str] = None, top_n: int = 10):
        # Resolve automaticamente para <raiz_do_projeto>/data/survey_results_public.csv
        # ou usa a variável de ambiente SURVEY_CSV_PATH (ideal para Docker)
        default_path = (
            Path(__file__).resolve().parents[3] / "data" / "survey_results_public.csv"
        )
        self.csv_path = csv_path or os.getenv("SURVEY_CSV_PATH", str(default_path))
        self.top_n = top_n
        self._df: Optional[pd.DataFrame] = None
        self._role_cache: Dict[str, List[str]] = {}

    def _load_dataframe(self) -> Optional[pd.DataFrame]:
        """Carrega o CSV apenas uma vez e mantém em memória apenas as colunas necessárias."""
        if self._df is not None:
            return self._df

        if not os.path.exists(self.csv_path):
            logger.error(f"Dataset do Stack Overflow não encontrado em: {self.csv_path}")
            return None

        try:
            colunas_disponiveis = pd.read_csv(self.csv_path, nrows=0).columns.tolist()
            colunas_para_ler = [self.COLUNA_CARGO] + [
                col for col in self.COLUNAS_ALVO.values() if col in colunas_disponiveis
            ]

            logger.info(f"Carregando dataset de requisitos: {self.csv_path}")
            self._df = pd.read_csv(
                self.csv_path, usecols=colunas_para_ler, low_memory=False
            )
            return self._df
        except Exception as e:
            logger.error(f"Erro ao carregar dataset '{self.csv_path}': {e}")
            return None

    def _filtrar_por_cargo(self, df: pd.DataFrame, cargo: str) -> pd.DataFrame:
        """Filtra o dataset pelo cargo digitado, com suporte a aliases PT -> EN."""
        cargo_limpo = cargo.strip()
        if not cargo_limpo:
            return pd.DataFrame()

        # 1. Tentativa direta (ex.: "DevOps", "Back-end")
        df_cargo = df[
            df[self.COLUNA_CARGO].str.contains(
                cargo_limpo, case=False, na=False, regex=False
            )
        ]
        if not df_cargo.empty:
            return df_cargo

        # 2. Tentativa via mapeamento de termos em português
        cargo_lower = cargo_limpo.lower()
        for termo_pt, termo_en in self.ROLE_ALIASES.items():
            if termo_pt in cargo_lower:
                df_cargo = df[
                    df[self.COLUNA_CARGO].str.contains(
                        termo_en, case=False, na=False, regex=False
                    )
                ]
                if not df_cargo.empty:
                    return df_cargo

        # 3. Tentativa por palavras individuais relevantes do título
        tokens = [t for t in re.findall(r"[a-zA-Z0-9\+#\-]{3,}", cargo_lower)]
        for token in tokens:
            df_cargo = df[
                df[self.COLUNA_CARGO].str.contains(
                    token, case=False, na=False, regex=False
                )
            ]
            if not df_cargo.empty:
                return df_cargo

        return pd.DataFrame()

    @staticmethod
    def _normalizar_nome_tech(tech: str) -> str:
        """Remove observações entre parênteses, ex.: 'Bash/Shell (all shells)' -> 'bash/shell'."""
        limpo = re.sub(r"\s*\([^)]*\)", "", tech).strip()
        return limpo.lower()

    def gerar_perfil_por_cargo(
        self, cargo: str, top_n: Optional[int] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Retorna o ranking percentual das tecnologias por categoria para o cargo informado,
        seguindo a lógica de análise do Stack Overflow Developer Survey.
        """
        limite = top_n or self.top_n
        df = self._load_dataframe()
        if df is None or self.COLUNA_CARGO not in df.columns:
            return {}

        df_cargo = self._filtrar_por_cargo(df, cargo)
        if df_cargo.empty:
            logger.warning(f"Nenhum registro encontrado no CSV para o cargo '{cargo}'.")
            return {}

        perfil: Dict[str, Dict[str, float]] = {}

        for categoria, nome_coluna in self.COLUNAS_ALVO.items():
            if nome_coluna not in df_cargo.columns:
                continue

            serie_valida = df_cargo[nome_coluna].dropna()
            total_respondentes_cat = len(serie_valida)
            if total_respondentes_cat == 0:
                continue

            contagem = (
                serie_valida.str.split(";")
                .explode()
                .str.strip()
                .value_counts()
                .head(limite)
            )
            percentuais = (contagem / total_respondentes_cat) * 100
            perfil[categoria] = {
                str(tech): round(float(pct), 1) for tech, pct in percentuais.items()
            }

        return perfil

    def gerar_dicionario_por_cargo(
        self, cargo: str, top_n: Optional[int] = None
    ) -> List[str]:
        """
        Gera dinamicamente a lista ordenada de tecnologias (dicionário do cargo)
        a partir do ranking percentual no CSV do Stack Overflow.
        """
        chave_cache = f"{cargo.strip().lower()}:{top_n or self.top_n}"
        if chave_cache in self._role_cache:
            return self._role_cache[chave_cache]

        perfil = self.gerar_perfil_por_cargo(cargo, top_n=top_n)
        if not perfil:
            return []

        # Consolida as tecnologias mantendo o maior percentual caso apareça em mais de uma coluna
        scores: Dict[str, float] = {}
        for techs_pct in perfil.values():
            for tech, pct in techs_pct.items():
                nome_norm = self._normalizar_nome_tech(tech)
                if not nome_norm:
                    continue
                # Separa tecnologias compostas com '/' (ex.: 'html/css' -> 'html', 'css')
                partes = [p.strip() for p in nome_norm.split("/") if p.strip()]
                for parte in partes:
                    if parte not in scores or pct > scores[parte]:
                        scores[parte] = pct

        dicionario_ordenado = [
            tech for tech, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]

        self._role_cache[chave_cache] = dicionario_ordenado
        return dicionario_ordenado

    def _extract_tags_sync(
        self, title: str, cargo: Optional[str] = None, description: str = ""
    ) -> List[str]:
        """Gera o dicionário para o cargo e identifica as tecnologias aplicáveis à vaga."""
        cargo_referencia = (cargo or title).strip()
        dicionario_dinamico = self.gerar_dicionario_por_cargo(cargo_referencia)

        if not dicionario_dinamico:
            return ["desenvolvimento", "tecnologia"]

        texto_busca = f"{title} {description}".lower()
        matched: List[str] = []

        for tech in dicionario_dinamico:
            # Regex com fronteira segura para evitar falsos positivos (ex.: 'r' em 'desenvolvedor')
            pattern = rf"(?<![a-z0-9\+#]){re.escape(tech)}(?![a-z0-9\+#])"
            if re.search(pattern, texto_busca):
                matched.append(tech)

        # Se o título/descrição não citar explicitamente nenhuma stack,
        # retorna as top 5 tecnologias mais demandadas no survey para aquele cargo
        if matched:
            return matched

        return dicionario_dinamico[:5]

    async def extract_tags(
        self, title: str, cargo: Optional[str] = None, description: str = ""
    ) -> List[str]:
        """Extrai as tecnologias essenciais da vaga usando o dicionário dinâmico do CSV."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._extract_tags_sync, title, cargo, description
        )