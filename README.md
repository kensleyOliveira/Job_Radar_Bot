# Job Radar Bot (Telegram + DDD + Docker)

Projeto completo de monitoramento e radar inteligente de vagas de tecnologia com arquitetura orientada a domínio (Domain-Driven Design), raspagem assíncrona, deduplicação SHA-256 e enriquecimento dos 7 pilares de carreira.

---

## 🏗 Arquitetura DDD

O projeto segue estritamente a separação em camadas:
- **`app/domain`**: Entidades puras (`Job`, `Course`, `SearchSubscription`), contratos de repositórios e regras de negócio invariantes (ex: cálculo de hash determinístico).
- **`app/application`**: Casos de uso (`SubscribeRoleUseCase`, `ProcessRadarUseCase`) desacoplados de frameworks e transportes.
- **`app/infrastructure`**: Implementações tecnológicas:
  - Banco de Dados com SQLAlchemy 2.0 Async e PostgreSQL.
  - Mensageria e agendador com Redis e Celery Beat.
  - Scrapers com `curl-cffi` (impersonação TLS Chrome) e `BeautifulSoup4`.
  - Integrações externas de enriquecimento (StackOverflow Tags, YouTube, Udemy).
- **`app/presentation`**: Handlers do Telegram orientados a eventos com `aiogram 3.x`.

---

## 🚀 Como Executar em 3 Passos

### 1. Configurar o Ambiente
Copie o `.env.example` para `.env` e adicione o token do seu bot obtido no [@BotFather](https://t.me/BotFather):
```bash
cp .env.example .env
nano .env # Insira seu TELEGRAM_BOT_TOKEN

```

### 2. Subir Todos os Serviços com Docker Compose

```bash
docker compose up --build -d

```

Isso iniciará:

1. `postgres` (Banco relacional)
2. `redis` (Fila do Celery e cache)
3. `bot` (Aplicação Telegram em polling assíncrono)
4. `celery_worker` (Processamento pesado de scraping)
5. `celery_beat` (Agendador de varredura periódica)

### 3. Testar no Telegram

Abra seu bot no Telegram e execute:

```text
/start
/buscar

```

1. Digite o cargo (ex.: `Desenvolvedor Python` ou `Data Scientist`).
2. Clique no botão com a duração desejada: **15, 30, 45 ou 60 dias**.
3. O sistema registrará a assinatura e começará a monitorar vagas inéditas!
"""

# Write all files to disk

for path, content in files.items():
full_path = os.path.join(base_dir, path)
os.makedirs(os.path.dirname(full_path), exist_ok=True)
with open(full_path, "w", encoding="utf-8") as f:
f.write(content)

# Create zip archive

zip_path = "/tmp/job_radar_ddd_project.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
for root, _, filenames in os.walk(base_dir):
for fn in filenames:
abs_file = os.path.join(root, fn)
rel_file = os.path.relpath(abs_file, base_dir)
zipf.write(abs_file, rel_file)

print(f"Project built successfully. Zip size: {os.path.getsize(zip_path)} bytes.")

```

```text?code_stdout&code_event_index=1
Project built successfully. Zip size: 15282 bytes.


```

O projeto foi estruturado seguindo os princípios de **Domain-Driven Design (DDD)**, **Clean Architecture**, conteinerização com **Docker** e execução assíncrona com **Telegram (aiogram 3.x)**, **PostgreSQL**, **Redis** e **Celery**.

Abaixo está a documentação técnica completa do código gerado, os arquivos e o passo a passo para torná-lo executável.

---

### 1. Estrutura de Diretórios (Domain-Driven Design)

```text
job_radar_bot/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
└── app/
    ├── __init__.py
    ├── main.py                                  # Entrypoint do sistema e polling do bot
    ├── domain/                                  # CAMADA DE DOMÍNIO (Regras e Entidades)
    │   ├── entities/
    │   │   ├── job.py                           # Entidade Job, Course e cálculo de Hash SHA-256
    │   │   └── subscription.py                  # Entidade SearchSubscription (15, 30, 45, 60 dias)
    │   └── repositories/
    │       ├── job_repository.py                # Interface abstrata do repositório de vagas
    │       └── subscription_repository.py       # Interface abstrata de assinaturas
    ├── application/                             # CASOS DE USO (Application Layer)
    │   └── use_cases/
    │       ├── subscribe_role.py                # Caso de uso: cadastrar período de busca
    │       └── process_radar.py                 # Orquestração do ciclo de scraping e deduplicação
    ├── infrastructure/                          # INFRAESTRUTURA & TECNOLOGIAS EXTERNAS
    │   ├── database/
    │   │   ├── models.py                        # Tabelas SQLAlchemy (Jobs, Subscriptions, Logs)
    │   │   └── session.py                       # Conexão assíncrona PostgreSQL via asyncpg
    │   ├── repositories/
    │   │   ├── sql_job_repository.py            # Implementação do repositório de vagas
    │   │   └── sql_subscription_repository.py   # Implementação do repositório de assinaturas
    │   ├── scrapers/
    │   │   └── linkedin_scraper.py              # Scraper furtivo com curl-cffi (TLS impersonation)
    │   ├── services/
    │   │   └── enrichment_service.py            # Validação StackOverflow + Cursos YouTube/Udemy
    │   ├── tasks/
    │   │   └── celery_app.py                    # Agendamento periódico Celery Beat + Workers
    │   └── telegram/
    │       └── bot_service.py                   # Envio estruturado dos 7 pilares no Telegram
    └── presentation/                            # INTERFACE DE USUÁRIO
        └── telegram/
            └── handlers.py                      # Fluxo de comandos (/start, /buscar, botões de dias)

```

---

### 2. Arquivos de Configuração e Virtualização

#### `requirements.txt`

```text
python-dotenv==1.0.1
pydantic==2.8.2
pydantic-settings==2.4.0
aiogram==3.12.0
SQLAlchemy==2.0.32
asyncpg==0.29.0
alembic==1.13.2
celery==5.4.0
redis==5.0.8
httpx==0.27.0
curl-cffi==0.7.1
beautifulsoup4==4.12.3
lxml==5.3.0
playwright==1.46.0
google-api-python-client==2.142.0

```

#### `Dockerfile`

```dockerfile
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instala browsers furtivos para scraping
RUN playwright install chromium --with-deps

COPY . .

CMD ["python", "-m", "app.main"]

```

#### `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: job_radar_postgres
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-job_radar_db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres} -d ${DB_NAME:-job_radar_db}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: job_radar_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: job_radar_bot
    restart: always
    command: python -m app.main
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: job_radar_worker
    restart: always
    command: celery -A app.infrastructure.tasks.celery_app worker --loglevel=info -c 2
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: job_radar_beat
    restart: always
    command: celery -A app.infrastructure.tasks.celery_app beat --loglevel=info
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:

```

#### `.env.example`

```env
# Obtenha em https://t.me/BotFather
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Banco de Dados
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=job_radar_db
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/job_radar_db

# Redis & Celery
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# Chave opcional para a API do YouTube v3
YOUTUBE_API_KEY=sua_chave_aqui

```

---

### 3. Código Principal da Arquitetura DDD

#### Entidade de Domínio e Deduplicação (`app/domain/entities/job.py`)

```python
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Course:
    title: str
    url: str
    platform: str  # "YouTube" | "Udemy"
    provider_or_channel: str
    is_paid: bool

@dataclass
class Job:
    title: str
    company_name: str
    location: str
    work_regime: str  # Remoto, Híbrido, Presencial
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
        # Garante idempotência: mesma vaga = mesmo hash SHA-256
        unique_string = f"{self.company_name.lower().strip()}_{self.title.lower().strip()}_{self.location.lower().strip()}_{self.external_id or ''}"
        return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()

```

#### Entidade de Assinatura Temporal (`app/domain/entities/subscription.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class SearchSubscription:
    telegram_chat_id: int
    role: str
    duration_days: int  # 15, 30, 45, 60
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(init=False)
    id: int | None = None

    def __post_init__(self):
        self.expires_at = self.created_at + timedelta(days=self.duration_days)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

```

#### Caso de Uso de Varredura e Deduplicação (`app/application/use_cases/process_radar.py`)

```python
class ProcessRadarUseCase:
    def __init__(self, subscription_repo, job_repo, scraper_service, enrichment_service, notification_service):
        self.subscription_repo = subscription_repo
        self.job_repo = job_repo
        self.scraper_service = scraper_service
        self.enrichment_service = enrichment_service
        self.notification_service = notification_service

    async def execute(self):
        # 1. Desativa assinaturas cujo prazo (15, 30, 45 ou 60 dias) já expirou
        await self.subscription_repo.deactivate_expired()
        active_subs = await self.subscription_repo.get_active_subscriptions()

        # 2. Agrupa por cargo para otimizar requisições aos scrapers
        role_map = {}
        for sub in active_subs:
            role_map.setdefault(sub.role.lower().strip(), []).append(sub)

        # 3. Executa a raspagem para cada cargo ativo
        for role, subs in role_map.items():
            scraped_jobs = await self.scraper_service.search_jobs(role)

            for raw_job in scraped_jobs:
                # Deduplicação no banco: descarta imediatamente se já foi minerada
                if await self.job_repo.exists_by_hash(raw_job.job_hash):
                    continue

                # 4. Enriquece com os 7 pilares (StackOverflow + Glassdoor + Cursos)
                enriched_job = await self.enrichment_service.enrich(raw_job)
                saved_job = await self.job_repo.save(enriched_job)

                # 5. Notifica todos os chats inscritos nesse cargo que ainda não receberam esta vaga
                for sub in subs:
                    if not await self.job_repo.was_notified(sub.id, saved_job.id):
                        await self.notification_service.send_job_alert(sub.telegram_chat_id, saved_job)
                        await self.job_repo.mark_notified(sub.id, saved_job.id)

```

#### Handlers do Telegram com Seleção de Vigência (`app/presentation/telegram/handlers.py`)

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class SearchStates(StatesGroup):
    waiting_for_role = State()

def get_duration_keyboard(role: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="15 Dias", callback_data=f"dur:15:{role}"),
            InlineKeyboardButton(text="30 Dias", callback_data=f"dur:30:{role}"),
        ],
        [
            InlineKeyboardButton(text="45 Dias", callback_data=f"dur:45:{role}"),
            InlineKeyboardButton(text="60 Dias", callback_data=f"dur:60:{role}"),
        ]
    ])

@router.message(Command("buscar"))
async def cmd_search(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_role)
    await message.answer(
        "🔎 *Qual cargo ou tecnologia você deseja monitorar?*\n"
        "_(Ex.: Desenvolvedor Python, Engenheiro de Dados, DevOps, etc.)_",
        parse_mode="Markdown"
    )

@router.message(SearchStates.waiting_for_role)
async def process_role_input(message: Message, state: FSMContext):
    role = message.text.strip()
    await state.clear()
    await message.answer(
        f"🎯 Perfeito! Por quanto tempo devo manter o radar ativo para *{role}*?",
        reply_markup=get_duration_keyboard(role),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("dur:"))
async def process_duration_selection(callback: CallbackQuery):
    _, days, role = callback.data.split(":")
    days = int(days)
    chat_id = callback.from_user.id

    from app.infrastructure.database.session import AsyncSessionLocal
    from app.infrastructure.repositories.sql_subscription_repository import SqlSubscriptionRepository
    from app.application.use_cases.subscribe_role import SubscribeRoleUseCase

    async with AsyncSessionLocal() as session:
        repo = SqlSubscriptionRepository(session)
        use_case = SubscribeRoleUseCase(repo)
        sub = await use_case.execute(chat_id=chat_id, role=role, days=days)

    await callback.message.edit_text(
        f"✅ *Radar Ativado!*\n\n"
        f"📌 *Cargo:* {role}\n"
        f"⏱ *Período de Monitoramento:* {days} dias (Até {sub.expires_at.strftime('%d/%m/%Y')})\n\n"
        f"O robô fará varreduras periódicas e enviará novas oportunidades inéditas diretamente neste chat.",
        parse_mode="Markdown"
    )

```

---

### 4. URLs e Endpoints Utilizados no Pipeline

| Finalidade | URL Base | Método de Acesso |
| --- | --- | --- |
| **Vagas LinkedIn (Guest API)** | `[https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search](https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search)` | Requisição HTTP rápida com `curl-cffi` (impersonação Chrome TLS) |
| **StackOverflow Tags** | `[https://api.stackexchange.com/2.3/tags](https://api.stackexchange.com/2.3/tags)` | API REST JSON para validação léxica das tecnologias |
| **Glassdoor (Métricas)** | `[https://www.glassdoor.com.br/index.htm](https://www.glassdoor.com.br/index.htm)` | Headless Chromium com evasão de fingerprint |
| **Cursos Gratuitos (YouTube)** | `[https://www.googleapis.com/youtube/v3/search](https://www.googleapis.com/youtube/v3/search)` | YouTube Data API v3 oficial |
| **Cursos Certificados (Udemy)** | `[https://www.udemy.com/api-2.0/courses/](https://www.udemy.com/api-2.0/courses/)` | API de Afiliados / XHR Query de catálogo |

---

### 5. Como Tornar o Projeto Executável

#### Opção A: Execução Conteinerizada com Docker Compose (Recomendada)

1. **Clone ou extraia o repositório:**
```bash
cd job_radar_bot

```


2. **Crie o arquivo de variáveis de ambiente:**
```bash
cp .env.example .env

```


Abra o `.env` e insira seu token gerado pelo [@BotFather](https://t.me/BotFather) na variável `TELEGRAM_BOT_TOKEN`.
3. **Suba todo o cluster com um único comando:**
```bash
docker compose up --build -d

```


4. **Verifique se todos os containers estão saudáveis:**
```bash
docker compose ps

```


Você verá:
* `job_radar_postgres` (Up / healthy)
* `job_radar_redis` (Up / healthy)
* `job_radar_bot` (Up - ouvindo o Telegram)
* `job_radar_worker` (Up - processando tarefas de scraping)
* `job_radar_beat` (Up - agendador dos ciclos de 15 a 60 dias)


5. **Acompanhe os logs em tempo real:**
```bash
docker compose logs -f bot celery_worker

```



---

#### Opção B: Execução Local (Ambiente Virtual Python)

Caso prefira rodar sem Docker diretamente em sua máquina:

1. **Crie e ative o ambiente virtual:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

```


2. **Instale as dependências e o navegador do Playwright:**
```bash
pip install -r requirements.txt
playwright install chromium

```


3. **Certifique-se de ter o PostgreSQL e Redis rodando localmente** e ajuste o arquivo `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/job_radar_db
REDIS_URL=redis://localhost:6379/0
TELEGRAM_BOT_TOKEN=seu_token_aqui

```


4. **Inicie os 3 processos em terminais separados:**
* **Terminal 1 (Bot do Telegram):**
```bash
python -m app.main

```


* **Terminal 2 (Worker de Scraping):**
```bash
celery -A app.infrastructure.tasks.celery_app worker --loglevel=info

```


* **Terminal 3 (Agendador Beat):**
```bash
celery -A app.infrastructure.tasks.celery_app beat --loglevel=info

```
