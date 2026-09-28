from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class SearchStates(StatesGroup):
    waiting_for_role = State()
    waiting_for_duration = State()

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

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Olá! Bem-vindo ao *Radar de Vagas Pro*!\n\n"
        "Eu monitoro continuamente o mercado para você, buscando vagas, validando requisitos técnicos com StackOverflow, "
        "checando cultura/salário e indicando cursos gratuitos e pagos para você preencher os requisitos.\n\n"
        "Comandos disponíveis:\n"
        "/buscar - Iniciar monitoramento de um cargo\n"
        "/ajuda - Explicar o funcionamento",
        parse_mode="Markdown"
    )

@router.message(Command("buscar"))
async def cmd_search(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_role)
    await message.answer(
        "🔎 Qual cargo ou área você deseja monitorar?\n*(Exemplo: Desenvolvedor Python, Data Scientist, DevOps)*",
        parse_mode="Markdown"
    )

@router.message(SearchStates.waiting_for_role)
async def process_role_input(message: Message, state: FSMContext):
    role = message.text.strip()
    await state.update_data(role=role)
    await state.set_state(SearchStates.waiting_for_duration)
    await message.answer(
        f"Ótimo! Por quanto tempo devo manter o radar ativo para *{role}*?",
        reply_markup=get_duration_keyboard(role),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("dur:"))
async def process_duration_selection(callback: CallbackQuery, state: FSMContext):
    _, days, role = callback.data.split(":")
    days = int(days)
    chat_id = callback.from_user.id

    from app.infrastructure.database.session import AsyncSessionLocal
    from app.infrastructure.repositories.sql_subscription_repository import SqlSubscriptionRepository
    from app.infrastructure.repositories.sql_job_repository import SqlJobRepository
    from app.infrastructure.scrapers.linkedin_scraper import LinkedInScraperService
    from app.infrastructure.services.enrichment_service import DataEnrichmentService
    from app.infrastructure.telegram.bot_service import TelegramNotificationService
    from app.application.use_cases.subscribe_role import SubscribeRoleUseCase

    await callback.message.edit_text(
        f"⏳ *Ativando radar para '{role}' e buscando vagas disponíveis...*",
        parse_mode="Markdown"
    )

    async with AsyncSessionLocal() as session:
        sub_repo = SqlSubscriptionRepository(session)
        job_repo = SqlJobRepository(session)
        scraper = LinkedInScraperService()
        enrichment = DataEnrichmentService()
        notification = TelegramNotificationService(callback.bot)

        use_case = SubscribeRoleUseCase(sub_repo, job_repo, scraper, enrichment, notification)
        sub = await use_case.execute(chat_id=chat_id, role=role, days=days)

    await callback.message.answer(
        f"✅ *Radar Ativado com Sucesso!*\n\n"
        f"🎯 *Cargo:* {role}\n"
        f"⏱ *Vigência:* {days} dias (Até {sub.expires_at.strftime('%d/%m/%Y')})\n\n"
        f"As vagas encontradas no momento já foram enviadas acima! Novas oportunidades serão enviadas automaticamente.",
        parse_mode="Markdown"
    )
    await state.clear()