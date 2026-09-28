```markdown
# 🎯 Radar de Vagas Pro (Job Radar Bot)

Um ecossistema automatizado e inteligente para monitorização contínua de vagas de emprego no LinkedIn e portais do mercado, com enriquecimento de dados (faixa salarial, avaliação de cultura no Glassdoor, requisitos técnicos e cursos recomendados) e notificações instantâneas via Telegram.

Projetado para operar de forma económica e distribuída, com suporte a **PostgreSQL na nuvem (Neon)**, **Docker** e execução agendada automática com **GitHub Actions**.

---

## 🚀 Funcionalidades

- **Monitorização Ativa e Flexível:**
  - Registo de pesquisas personalizadas por cargo através do Telegram (`/buscar`).
  - Definição de prazo de vigência para cada monitorização (15, 30, 45 ou 60 dias).
  - Normalização multilíngue (português, inglês e espanhol) via radicais léxicos (*stems*) e filtros de contexto.
- **Scraping Resiliente:**
  - Extração de oportunidades reais no LinkedIn com recurso a browsers *headless* (Playwright).
- **Enriquecimento Inteligente de Dados:**
  - **Estimativa Salarial:** Raspagem em tempo real de portais de remuneração com *TLS fingerprinting*.
  - **Cultura e Reputação da Empresa:** Recolha da avaliação média (estrelas) no Glassdoor.
  - **Requisitos Técnicos:** Identificação de linguagens, ferramentas e competências exigidas no título e na descrição.
  - **Recomendação de Cursos:** Sugestões diretas de cursos gratuitos (YouTube) e pagos (Udemy) focados nas tecnologias da vaga.
- **Deduplicação Global por Utilizador:**
  - Cruzamento de dados que garante que o utilizador nunca recebe a mesma oportunidade duas vezes, mesmo que recrie a subscrição ou altere o período de monitorização.
- **Arquitetura Nuvem de Baixo Custo:**
  - Integração com PostgreSQL serverless na nuvem (Neon).
  - Execuções periódicas agendadas via GitHub Actions (CI/CD) sem custos adicionais de servidores dedicados.

---

## 🏗 Arquitetura do Projeto e Fluxo de Dados

O projeto adota os princípios da **Clean Architecture** (Arquitetura Limpa) e **Domain-Driven Design (DDD)**, isolando regras de negócio de ferramentas externas, e recorre a um modelo híbrido para manter o funcionamento gratuito.

### Estrutura de Camadas
- `app/domain/`: Entidades de negócio (`Job`, `SearchSubscription`, `Course`) e contratos de repositórios.
- `app/application/`: Casos de uso (`ProcessRadarUseCase`, `SubscribeRoleUseCase`).
- `app/infrastructure/`: Implementações concretas de base de dados (SQLAlchemy assíncrono), scrapers (Playwright), cliente Telegram (Aiogram) e serviços de enriquecimento.
- `app/presentation/`: Handlers de mensagens, estados de conversação (FSM) e menus interativos do Telegram.

### Estrutura de Diretórios (Domain-Driven Design)

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

### Diagrama de Fluxo

```text
┌───────────────────────┐
│  Utilizador (Telegram) │ ── envia /buscar e escolhe os dias
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│     Aiogram Bot       │ ── regista subscrição e envia vagas existentes
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│      Neon Nuvem       │ ◄── Base de Dados PostgreSQL Central
│   (Tabelas Globais)   │     (jobs, search_subscriptions, notification_logs)
└───────────▲───────────┘
            │
            │ Conexão agendada (Cron: 09h, 14h, 19h)
            │
┌───────────┴───────────┐
│     GitHub Actions    │ ── 1. Lê subscrições ativas do Neon
│    (run_radar_cli)    │ ── 2. Raspa o LinkedIn (Playwright)
│                       │ ── 3. Enriquece salários e Glassdoor
│                       │ ── 4. Salva novas vagas no Neon
│                       │ ── 5. Envia alertas para o Telegram
│                       │ ── 6. Desliga o runner (0 consumo extra)
└───────────────────────┘

```

---

## 📦 Requisitos e Dependências

Para executar este projeto localmente ou num servidor, são necessários:

1. **Python 3.12+** instalado.
2. **Git** para clonar e versionar o código.
3. **Docker e Docker Compose** (opcional, mas recomendado para executar em contentores).
4. **Conta no Neon.tech** (PostgreSQL na nuvem gratuito).
5. **Token de Bot no Telegram** (obtido gratuitamente no [@BotFather](https://t.me/BotFather?utm_source=gemini)).

---

## 🛠 Guia Didático Passo a Passo: Configuração e Execução

### 1. Clonar o Repositório

Abra o seu terminal (ou PowerShell no Windows) e execute:

```bash
git clone [https://github.com/SEU_USUARIO/Job_Radar_Bot.git](https://github.com/SEU_USUARIO/Job_Radar_Bot.git)
cd Job_Radar_Bot

```

---

### 2. Configurar o Ambiente Virtual Python (Execução Local)

Recomenda-se a utilização de um ambiente virtual isolado:

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente no Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# (No Linux ou macOS, utilize: source venv/bin/activate)

```

Instale as dependências e os navegadores do Playwright:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium --with-deps

```

---

### 3. Configurar as Variáveis de Ambiente (`.env`)

Crie um ficheiro chamado `.env` na raiz do projeto:

```env
# Token obtido junto do @BotFather no Telegram
TELEGRAM_BOT_TOKEN=8583326217:AAFg...

# String de ligação do Neon (PostgreSQL) com driver assíncrono asyncpg e parâmetro ssl=require
DATABASE_URL=postgresql+asyncpg://neondb_owner:SUA_SENHA@ep-xyz-pooler.sa-east-1.aws.neon.tech/neondb?ssl=require

# Configuração opcional de Redis (se optar por executar o worker Celery localmente)
REDIS_URL=redis://localhost:6379/0

```

> **Atenção:** Assegure-se de que a `DATABASE_URL` começa com `postgresql+asyncpg://` e termina com `ssl=require` para garantir a compatibilidade com a biblioteca `asyncpg`.

---

### 4. Como Executar

#### Opção A: Execução Local Rápida (Desenvolvimento / Interação com o Bot)

Para iniciar o bot e poder registar pesquisas através do Telegram (`/buscar`):

```bash
python -m app.main

```

Para testar a raspagem imediata e o envio pontual de alertas diretamente pela linha de comandos:

```bash
python run_radar_cli.py

```

---

#### Opção B: Execução Completa com Docker Compose

Se preferir executar o bot e as filas num ambiente com contentores isolados:

```bash
docker compose up --build -d bot

```

Para consultar os registos e acompanhar o processamento:

```bash
docker compose logs -f bot

```

---

### 5. Configurar a Execução Agendada Gratuita (GitHub Actions)

Para que o radar funcione de forma autónoma sem ser necessário manter o computador ligado:

1. Aceda ao seu repositório no GitHub e vá a **Settings** > **Secrets and variables** > **Actions**.
2. Adicione os dois segredos através do botão **New repository secret**:
* `DATABASE_URL`: A ligação completa do Neon (`postgresql+asyncpg://...`).
* `TELEGRAM_BOT_TOKEN`: O token do seu bot Telegram.


3. No separador **Actions** do GitHub, selecione **Radar de Vagas Agendado** e clique em **Run workflow** para testar.
4. O GitHub passará a executar o varrimento três vezes ao dia (09:00, 14:00 e 19:00 UTC) e enviará as novas vagas automaticamente para o seu Telegram.

---

## 📋 Comandos do Telegram

* `/start` - Apresentação do bot e instruções de utilização.
* `/buscar` - Inicia o assistente de registo:
1. O bot pergunta qual é o cargo pretendido (ex: `Engenheiro de Dados`, `Frontend Developer`, `Java`).
2. Apresenta botões para escolher o período de acompanhamento (15, 30, 45 ou 60 dias).
3. Devolve na hora as vagas compatíveis já registadas e passa a vigiar novas oportunidades.


* `/ajuda` - Explicação detalhada sobre o funcionamento e cálculo de médias.

```
---
