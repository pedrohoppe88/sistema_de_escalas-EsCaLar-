"""
Serviços de geração de PDFs para o sistema de sargenteação.
"""
from datetime import date, timedelta
from typing import Dict, List
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from .models import Servico
from .services import ADITAMENTO_SECTIONS, TIPO_SERVICO_LABELS


def gerar_aditamento_pdf(data: date, servicos) -> HttpResponse:
    """
    Gera o PDF do aditamento para uma data específica.
    
    Args:
        data: Data de referência
        servicos: QuerySet de serviços
        
    Returns:
        HttpResponse com o PDF
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="aditamento_{data.strftime("%d_%m_%Y")}.pdf"'
    )

    c = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    y = altura - 50

    # 🪖 Cabeçalho
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
    y -= 28
    c.setLineWidth(1)
    c.line(50, y, largura - 50, y)
    y -= 18

    c.setFont("Helvetica", 11)
    c.drawCentredString(
        largura / 2, y,
        f"Serviço do dia {data.strftime('%d/%m/%Y')}"
    )

    y -= 32

    # 📋 Agrupado por tipo de serviço
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Serviços por Tipo")
    y -= 18
    c.setLineWidth(0.7)
    c.line(50, y, largura - 50, y)
    y -= 16

    c.setFont("Helvetica", 10)

    if not servicos.exists():
        c.drawString(50, y, "Nenhum militar escalado.")
    else:
        for tipo, titulo in ADITAMENTO_SECTIONS:
            # Seção do tipo
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, titulo)
            y -= 14

            entries = servicos.filter(tipo=tipo)

            if not entries.exists():
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(60, y, "— Nenhum militar neste tipo —")
                y -= 16
            else:
                c.setFont("Helvetica", 10)
                for idx, s in enumerate(entries, start=1):
                    grad = s.militar.get_graduacao_display()
                    nome = s.militar.nome
                    texto = f"{idx}. {grad} — {nome}"
                    c.drawString(60, y, texto)
                    y -= 16

                    # Quebra de página
                    if y < 60:
                        c = _adicionar_pagina_aditamento(c, data, largura, altura)
                        y = altura - 50

            # Espaço entre seções
            y -= 10

    # 🖊️ Rodapé
    y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Sargenteação / Administração do Serviço")

    c.showPage()
    c.save()

    return response


def _adicionar_pagina_aditamento(c, data, largura, altura):
    """Adiciona uma nova página ao PDF do aditamento com cabeçalho."""
    c.showPage()
    y = altura - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
    y -= 28
    c.setLineWidth(1)
    c.line(50, y, largura - 50, y)
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawCentredString(largura / 2, y, f"Serviço do dia {data.strftime('%d/%m/%Y')}")
    y -= 32
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Serviços por Tipo")
    y -= 18
    c.setLineWidth(0.7)
    c.line(50, y, largura - 50, y)
    y -= 16
    return c


def gerar_relatorio_mensal_pdf(militar, servicos, mes: int, ano: int) -> HttpResponse:
    """
    Gera o PDF do relatório mensal de serviços de um militar.
    
    Args:
        militar: Instância do Militar
        servicos: QuerySet de serviços
        mes: Mês de referência
        ano: Ano de referência
        
    Returns:
        HttpResponse com o PDF
    """
    from calendar import month_name
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="relatorio_{militar.nome}_{mes}_{ano}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    y = altura - 50

    # 🧾 Cabeçalho
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "RELATÓRIO MENSAL DE SERVIÇOS")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Militar: {militar.nome}")
    y -= 20
    pdf.drawString(50, y, f"Mês/Ano: {month_name[mes].upper()} / {ano}")
    y -= 20
    pdf.drawString(50, y, f"Total de serviços: {servicos.count()}")
    y -= 30

    # 📋 Tabela simples
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "DATA DO SERVIÇO")
    y -= 15
    pdf.line(50, y, 300, y)
    y -= 15

    pdf.setFont("Helvetica", 11)

    if servicos.exists():
        for servico in servicos:
            pdf.drawString(50, y, servico.data.strftime('%d/%m/%Y'))
            y -= 18

            if y < 50:
                pdf.showPage()
                y = altura - 50
                pdf.setFont("Helvetica", 11)
    else:
        pdf.drawString(50, y, "Nenhum serviço registrado no período.")

    # 🪖 Rodapé
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, 30, "Documento gerado pelo Sistema de Sargenteação")

    pdf.showPage()
    pdf.save()

    return response


def gerar_pdf_simples(titulo: str, conteudo: List[str], filename: str) -> HttpResponse:
    """
    Gera um PDF simples genérico.
    
    Args:
        titulo: Título do documento
        conteudo: Lista de linhas de conteúdo
        filename: Nome do arquivo para download
        
    Returns:
        HttpResponse com o PDF
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    y = altura - 50

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura / 2, y, titulo)
    y -= 30

    # Conteúdo
    c.setFont("Helvetica", 12)
    for linha in conteudo:
        c.drawString(50, y, linha)
        y -= 18

        if y < 50:
            c.showPage()
            y = altura - 50
            c.setFont("Helvetica", 12)

    c.showPage()
    c.save()

    return response
