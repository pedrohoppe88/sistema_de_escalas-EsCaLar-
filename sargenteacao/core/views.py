from django.shortcuts import render
from .services import calcular_efetivo_do_dia
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Militar, Servico

from datetime import date
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import Servico

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .utils.permissoes import (
    pode_registrar_servico,
    pode_gerar_pdf
)
from django.shortcuts import render, get_object_or_404
from calendar import month_name


def efetivo_do_dia(request):
    efetivo = calcular_efetivo_do_dia()
    return render(request, 'core/efetivo_do_dia.html', {
        'efetivo': efetivo
    })
    
def registrar_servico(request):
    hoje = date.today()

    # Usa o Efetivo do Dia (regra centralizada)
    efetivo = calcular_efetivo_do_dia()

    # Apenas militares APTOS
    militares_aptos = [e for e in efetivo if e['apto']]

    if request.method == 'POST':
        selecionados = request.POST.getlist('militares')

        for item in militares_aptos:
            militar = item['militar']

            if str(militar.id) in selecionados:

                # ❌ Regra 1: não duplicar serviço no mesmo dia
                if Servico.objects.filter(militar=militar, data=hoje).exists():
                    continue

                # ❌ Regra 2: garantir que é apto
                if not item['apto']:
                    continue

                # ✅ Registrar serviço
                Servico.objects.create(
                    militar=militar,
                    data=hoje
                )

        messages.success(request, '✅ Serviço registrado com sucesso')
        return redirect('efetivo_do_dia')

    return render(request, 'core/registrar_servico.html', {
        'militares': militares_aptos
    })
    
def gerar_aditamento_pdf(request):
    hoje = date.today()

    servicos = Servico.objects.filter(data=hoje).select_related('militar')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="aditamento_{hoje.strftime("%d_%m_%Y")}.pdf"'
    )

    c = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    y = altura - 50

    # 🪖 Cabeçalho
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
    y -= 25

    c.setFont("Helvetica", 11)
    c.drawCentredString(
        largura / 2, y,
        f"Serviço do dia {hoje.strftime('%d/%m/%Y')}"
    )

    y -= 40

    # 📋 Lista de militares
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "MILITARES ESCALADOS:")
    y -= 20

    c.setFont("Helvetica", 10)

    if not servicos.exists():
        c.drawString(50, y, "Nenhum militar escalado.")
    else:
        for idx, servico in enumerate(servicos, start=1):
            texto = f"{idx}. {servico.militar.nome}"
            c.drawString(60, y, texto)
            y -= 18

            # Quebra de página
            if y < 50:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = altura - 50

    # 🖊️ Rodapé
    y -= 40
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Sargenteação / Administração do Serviço")

    c.showPage()
    c.save()

    return response

@login_required
def registrar_servico(request):
    if not pode_registrar_servico(request.user):
        return HttpResponseForbidden("Você não tem permissão para registrar serviço.")

    # lógica de registro aqui
    
@login_required
def gerar_aditamento_pdf(request):
    if not pode_gerar_pdf(request.user):
        return HttpResponseForbidden("Apenas o sargenteante pode gerar o aditamento.")

    # código do PDF aqui
@login_required
def historico_militar(request, militar_id):

    # 🔐 Regra de acesso
    if not pode_gerar_pdf(request.user):
        return HttpResponseForbidden("Você não tem permissão para acessar este histórico.")

    militar = get_object_or_404(Militar, id=militar_id)

    servicos = Servico.objects.filter(
        militar=militar
    ).order_by('-data')

    hoje = date.today()

    total_servicos = servicos.count()
    ultimo_servico = servicos.first()

    total_mes = servicos.filter(
        data__month=hoje.month,
        data__year=hoje.year
    ).count()

    context = {
        'militar': militar,
        'servicos': servicos,
        'total_servicos': total_servicos,
        'ultimo_servico': ultimo_servico,
        'total_mes': total_mes,
    }

    return render(request, 'core/historico_militar.html', context)

@login_required
def relatorio_mensal_militar_pdf(request, militar_id, ano, mes):

    if not pode_gerar_pdf(request.user):
        return HttpResponseForbidden("Você não tem permissão para gerar este relatório.")

    militar = get_object_or_404(Militar, id=militar_id)

    servicos = Servico.objects.filter(
        militar=militar,
        data__year=ano,
        data__month=mes
    ).order_by('data')

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

@login_required
def admin_user_management(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Apenas superusuários podem acessar esta página.")

    from django.contrib.auth.models import User, Group
    users = User.objects.all()
    groups = Group.objects.all()

    context = {
        'users': users,
        'groups': groups,
    }

    return render(request, 'core/admin_user_management.html', context)
