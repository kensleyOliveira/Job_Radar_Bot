import os
import pytest
import aiohttp
from unittest.mock import patch, MagicMock
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from unittest.mock import patch, MagicMock, AsyncMock

from app.domain.entities.job import Course
from app.infrastructure.services.enrichment_service_B import DataEnrichmentService



# =====================================================================
# Função Auxiliar: Exportar e Formatar Planilha Excel
# =====================================================================
def export_courses_to_excel(courses_by_tag: dict[str, list[Course]], file_path: str = "cursos_recomendados.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Cursos Recomendados"

    # Ativa linhas de grade na visualização
    ws.views.sheetView[0].showGridLines = True

    # 1. Cabeçalho Principal (Título)
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = "🎓 Radar de Vagas - Catálogo de Cursos Recomendados"
    title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35

    # 2. Cabeçalhos das Colunas
    headers = ["Tecnologia / Tag", "Plataforma", "Título do Curso", "Instrutor / Canal", "Tipo", "Link de Acesso"]
    ws.append([])  # Linha 2 vazia
    ws.append(headers)  # Linha 3
    ws.row_dimensions[3].height = 25

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # 3. Inserção de Dados
    current_row = 4
    zebra_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")

    for tag, courses in courses_by_tag.items():
        for course in courses:
            tipo_label = "Pago" if course.is_paid else "Gratuito"
            
            ws.cell(row=current_row, column=1, value=tag.upper())
            ws.cell(row=current_row, column=2, value=course.platform)
            ws.cell(row=current_row, column=3, value=course.title)
            ws.cell(row=current_row, column=4, value=course.provider_or_channel)
            ws.cell(row=current_row, column=5, value=tipo_label)

            # Link clicável com formatação padrão de hiperlink
            link_cell = ws.cell(row=current_row, column=6, value="Acessar Curso")
            link_cell.hyperlink = course.url
            link_cell.font = Font(name="Calibri", size=10, color="0563C1", underline="single")

            # Aplica bordas e estilo zebrado alternado
            for col_idx in range(1, len(headers) + 1):
                c = ws.cell(row=current_row, column=col_idx)
                c.border = thin_border
                if current_row % 2 == 0 and col_idx != 6:
                    c.fill = zebra_fill
                if col_idx in [1, 2, 5, 6]:
                    c.alignment = Alignment(horizontal="center", vertical="center")

            current_row += 1

    # 4. Ajuste Automático da Largura das Colunas
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

    ws.column_dimensions["C"].width = 45  # Largura extra para o título do curso
    wb.save(file_path)
    return file_path


# =====================================================================
# Testes Unitários com Pytest
# =====================================================================
@pytest.fixture
def enrichment_service():
    return DataEnrichmentService()


@pytest.mark.asyncio
async def test_get_udemy_courses_fallback_when_no_credentials(enrichment_service):
    """Garante que sem credenciais o fallback de busca na Udemy é retornado."""
    with patch("app.infrastructure.services.enrichment_service.UDEMY_CLIENT_ID", ""), \
         patch("app.infrastructure.services.enrichment_service.UDEMY_CLIENT_SECRET", ""):
        
        async with aiohttp.ClientSession() as session:
            courses = await enrichment_service._get_udemy_courses("python", session)
            
            assert len(courses) == 1
            assert courses[0].platform == "Udemy"
            assert "python" in courses[0].url.lower()
            assert courses[0].is_paid is True


@pytest.mark.asyncio
async def test_get_udemy_courses_mock_api_success(enrichment_service):
    """Simula resposta 200 JSON da API da Udemy e valida o parsing."""
    mock_payload = {
        "results": [
            {
                "title": "Python do Zero ao Avançado",
                "url": "/course/python-completo/",
                "is_paid": True,
                "visible_instructors": [{"title": "Instrutor Teste"}]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_payload)
    mock_resp.__aenter__.return_value = mock_resp

    with patch("app.infrastructure.services.enrichment_service.UDEMY_CLIENT_ID", "dummy_id"), \
         patch("app.infrastructure.services.enrichment_service.UDEMY_CLIENT_SECRET", "dummy_secret"), \
         patch.object(aiohttp.ClientSession, "get", return_value=mock_resp):

        async with aiohttp.ClientSession() as session:
            courses = await enrichment_service._get_udemy_courses("python", session)

            assert len(courses) == 1
            assert courses[0].title == "Python do Zero ao Avançado"
            assert courses[0].provider_or_channel == "Instrutor Teste"
            assert courses[0].url == "https://www.udemy.com/course/python-completo/"

# =====================================================================
# Teste de Coleta & Exportação para Excel
# =====================================================================
@pytest.mark.asyncio
async def test_scrape_courses_and_export_excel(enrichment_service, tmp_path):
    """
    Executa a coleta de cursos para tecnologias reais via YouTube/Udemy (com ou sem credenciais)
    e exporta os resultados para um arquivo Excel formatado.
    """
    tags_to_test = ["python", "sql", "react"]
    collected_results: dict[str, list[Course]] = {}

    for tag in tags_to_test:
        courses = await enrichment_service.get_courses_for_tag(tag)
        assert len(courses) > 0, f"Nenhum curso foi obtido para a tag '{tag}'"
        collected_results[tag] = courses

    # Gera a planilha na raiz do projeto (ou no tmp_path para testes de CI)
    output_excel = "cursos_coletados_teste.xlsx"
    file_generated = export_courses_to_excel(collected_results, output_excel)

    assert os.path.exists(file_generated), "O arquivo Excel não foi gerado com sucesso."
    assert os.path.getsize(file_generated) > 0, "O arquivo Excel gerado está vazio."
    print(f"\n[SUCESSO] Planilha formatada gerada em: {os.path.abspath(file_generated)}")