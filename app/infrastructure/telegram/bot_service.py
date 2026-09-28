import html
from aiogram import Bot
from aiogram.enums import ParseMode
from app.domain.entities.job import Job


class TelegramNotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_job_alert(self, chat_id: int, job: Job):
       
        title = html.escape(job.title or "")
        company = html.escape(job.company_name or "")
        location = html.escape(job.location or "")
        work_regime = html.escape(job.work_regime or "")
        salary = html.escape(job.average_salary or "Não informado")
        description = html.escape(job.description or "")
        culture = f"{job.culture_rating:.1f}" if job.culture_rating else "N/A"

        # Tags técnicas formatadas como <code>#tag</code>
        tags = [f"<code>#{html.escape(t.strip())}</code>" for t in job.technical_requirements if t]
        tags_str = ", ".join(tags) if tags else "<i>Nenhuma especificada</i>"

        # 2. Formata lista de cursos com links clicáveis seguros
        courses_lines = []
        for c in job.courses[:3]:
            tipo = "Gratuito" if not c.is_paid else "Pago/Certificado"
            c_platform = html.escape(c.platform)
            c_title = html.escape(c.title)
            # Para URLs em tags <a>, escapamos apenas aspas e & via html.escape
            c_url = html.escape(c.url, quote=True)
            courses_lines.append(f"• [{c_platform} - {tipo}] <a href=\"{c_url}\">{c_title}</a>")

        courses_text = "\n".join(courses_lines) if courses_lines else "<i>Sem recomendações no momento</i>"
        apply_url_escaped = html.escape(job.apply_url, quote=True)

        # 3. Monta a mensagem com tags HTML válidas do Telegram (<b>, <i>, <code>, <a>)
        message = (
            f"🎯 <b>NOVA VAGA ENCONTRADA NO SEU RADAR!</b>\n\n"
            f"📌 <b>Cargo:</b> {title}\n"
            f"🏢 <b>Empresa:</b> {company} (⭐ {culture})\n"
            f"📍 <b>Local:</b> {location} | <b>Regime:</b> {work_regime}\n"
            f"💰 <b>Média Salarial:</b> {salary}\n\n"
            f"🛠 <b>Requisitos Técnicos:</b>\n{tags_str}\n\n"
            f"📝 <b>Descrição:</b>\n<i>{description}</i>\n\n"
            f"🎓 <b>Cursos Recomendados:</b>\n{courses_text}\n\n"
            f"🔗 <a href=\"{apply_url_escaped}\"><b>CANDIDATAR-SE AGORA</b></a>"
        )

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Erro ao enviar alerta para {chat_id}: {e}")