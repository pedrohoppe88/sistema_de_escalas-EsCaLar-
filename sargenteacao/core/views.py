from django.shortcuts import render
from .services import calcular_efetivo_do_dia, calcular_efetivo_por_data
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Militar, Servico, Afastamento
from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Militar, Afastamento
from .serializers import MilitarSerializer

from datetime import date
from django.http import HttpResponse
from django.http import JsonResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import Servico

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .utils.permissoes import (
    pode_registrar_servico,
    pode_gerar_relatorios,
    pode_gerenciar_militares,
    pode_gerenciar_afastamentos,
    pode_visualizar_efetivo,
    pode_gerenciar_usuarios,
    assign_default_group
)
from django.shortcuts import render, get_object_or_404
from calendar import month_name

# Authentication imports
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.forms import Form, CharField, PasswordInput, EmailInput, Select, TextInput

# Login Form
class LoginForm(Form):
    username = CharField(max_length=150, widget=TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nome de usuário',
        'type': 'text',
        'inputmode': 'text',
        'autocomplete': 'username',
        'style': 'background-image: none !important;'
    }))
    password = CharField(widget=PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha'}))

# Registration Form
class RegistrationForm(UserCreationForm):
    email = CharField(max_length=254, required=True, widget=EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    graduacao = CharField(max_length=20, required=True, widget=Select(choices=Militar.GRADUACOES_CHOICES, attrs={'class': 'form-control'}))

    class Meta:
        model = UserCreationForm.Meta.model
        fields = ('username', 'email', 'graduacao', 'password1', 'password2')
        widgets = {
            'username': TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome de usuário'}),
            'password1': PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha'}),
            'password2': PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar senha'}),
        }

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if pode_gerenciar_usuarios(user) or user.is_superuser:
                    return redirect('dashboard')
                return redirect('ver_efetivo')
            else:
                messages.error(request, 'Credenciais inválidas.')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

def login_moderno(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if pode_gerenciar_usuarios(user) or user.is_superuser:
                    return redirect('dashboard')
                return redirect('ver_efetivo')
            else:
                messages.error(request, 'Credenciais inválidas.')
    else:
        form = LoginForm()
    return render(request, 'core/login_moderno.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                # Create Militar instance with graduacao
                Militar.objects.create(
                    nome=user.username,
                    graduacao=form.cleaned_data['graduacao'],
                    subunidade='Padrão'  # Default subunidade
                )
                messages.success(request, 'Conta criada com sucesso! Faça o login.')
                return redirect('login')
            except Exception as e:
                user.delete()  # Rollback user creation if Militar fails
                messages.error(request, f'Erro ao criar conta: {str(e)}')
    else:
        form = RegistrationForm()
    return render(request, 'core/register.html', {'form': form})

def home(request):
    return render(request, 'core/home.html', {
        'project_name': 'EsCaLar'
    })

def logout_view(request):
    logout(request)
    messages.info(request, 'Você foi desconectado.')
    return redirect('login')


@login_required
def ver_efetivo(request):
    if not pode_visualizar_efetivo(request.user):
        return HttpResponseForbidden("Você não tem permissão para ver efetivo.")
    from datetime import datetime
    data_str = request.GET.get('data')
    try:
        data_ref = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else date.today()
    except ValueError:
        data_ref = date.today()
    efetivo = calcular_efetivo_por_data(data_ref)
    return render(request, 'core/efetivo_do_dia.html', {
        'efetivo': efetivo,
        'data_selecionada': data_ref,
        'can_reports': pode_gerar_relatorios(request.user),
    })

    
def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, 'core/erro_nao_logado.html', status=401)
    hoje = date.today()
    total_militares = Militar.objects.count()
    total_afastamentos_hoje = Afastamento.objects.filter(
        data_inicio__lte=hoje,
        data_fim__gte=hoje
    ).count()
    total_servicos_hoje = Servico.objects.filter(data=hoje).count()
    context = {
        'total_militares': total_militares,
        'total_afastamentos_hoje': total_afastamentos_hoje,
        'total_servicos_hoje': total_servicos_hoje,
        'hoje': hoje,
    }
    return render(request, 'core/dashboard.html', context)
    
    
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

    from datetime import datetime
    from django.urls import reverse

    data_str = request.GET.get('data') if request.method == 'GET' else request.POST.get('data')
    q = request.GET.get('q', '').strip()
    graduacao = request.GET.get('graduacao', '').strip()
    try:
        data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else date.today()
    except ValueError:
        data_selecionada = date.today()

    # Usa o Efetivo do Dia (regra centralizada)
    efetivo = calcular_efetivo_por_data(data_selecionada)

    # Apenas militares APTOS
    militares_aptos = []
    for e in efetivo:
        if e['apto']:
            if q and q.lower() not in e['militar'].nome.lower():
                continue
            if graduacao and e['militar'].graduacao != graduacao:
                continue
            grad = e['militar'].graduacao
            base = [
                ('GUARDA', 'Guarda ao Quartel'),
                ('PLANTAO', 'Plantão'),
                ('PERMANENCIA', 'Permanência'),
            ]
            extras = []
            if grad == '3SG':
                extras.append(('COMANDANTE_GUARDA', 'Comandante da Guarda'))
            if grad == 'CB':
                extras.append(('CABO_GUARDA', 'Cabo da Guarda'))
                extras.append(('CABO_DIA', 'Cabo de Dia'))
            if grad in ('2SG', '1SG'):
                extras.append(('ADJUNTO', 'Adjunto'))
            if grad in ('1TEN', '2TEN'):
                extras.append(('OFICIAL_DIA', 'Oficial de Dia'))
            e['opcoes_tipo'] = base + extras
            militares_aptos.append(e)
    militares_nao_aptos = [
        e for e in efetivo
        if not e['apto']
        and (not q or q.lower() in e['militar'].nome.lower())
        and (not graduacao or e['militar'].graduacao == graduacao)
    ]

    if request.method == 'POST':
        selecionados = request.POST.getlist('militares')

        for item in militares_aptos:
            militar = item['militar']

            if str(militar.id) in selecionados:

                # ❌ Regra 1: não duplicar serviço no mesmo dia
                if Servico.objects.filter(militar=militar, data=data_selecionada).exists():
                    continue

                # ❌ Regra 2: garantir que é apto
                if not item['apto']:
                    continue

                # ✅ Registrar serviço
                tipo = request.POST.get(f'tipo_{militar.id}', 'GUARDA')
                grad = militar.graduacao
                allowed = [
                    'GUARDA', 'PLANTAO', 'PERMANENCIA'
                ]
                if grad == '3SG':
                    allowed.append('COMANDANTE_GUARDA')
                if grad == 'CB':
                    allowed.append('CABO_GUARDA')
                    allowed.append('CABO_DIA')
                if grad in ('2SG', '1SG'):
                    allowed.append('ADJUNTO')
                if grad in ('1TEN', '2TEN'):
                    allowed.append('OFICIAL_DIA')
                if tipo not in allowed:
                    continue
                # ❌ Regra 3: cargos especiais são únicos por dia
                especiais = {'OFICIAL_DIA', 'ADJUNTO', 'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA'}
                if tipo in especiais and Servico.objects.filter(data=data_selecionada, tipo=tipo).exists():
                    messages.warning(request, f'Cargo {tipo.replace("_", " ").title()} já atribuído para {data_selecionada.strftime("%d/%m/%Y")}.')
                    continue
                Servico.objects.create(
                    militar=militar,
                    data=data_selecionada,
                    tipo=tipo,
                    registrado_por=request.user
                )

        messages.success(request, '✅ Serviço registrado com sucesso')
        return redirect(f"{reverse('registrar_servico')}?data={data_selecionada.isoformat()}")

    return render(request, 'core/registrar_servico.html', {
        'militares': militares_aptos,
        'nao_aptos': militares_nao_aptos,
        'data_selecionada': data_selecionada,
        'graduacoes': Militar.GRADUACOES_CHOICES,
        'q': q,
        'graduacao': graduacao
    })

@login_required
def gerar_aditamento_pdf(request):
    if not pode_gerar_relatorios(request.user):
        return HttpResponseForbidden("Você não tem permissão para gerar o aditamento.")

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
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
    y -= 28
    c.setLineWidth(1)
    c.line(50, y, largura - 50, y)
    y -= 18

    c.setFont("Helvetica", 11)
    c.drawCentredString(
        largura / 2, y,
        f"Serviço do dia {hoje.strftime('%d/%m/%Y')}"
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

    sections = [
        ('COMANDANTE_GUARDA', 'Comandante da Guarda'),
        ('CABO_GUARDA', 'Cabo da Guarda'),
        ('CABO_DIA', 'Cabo de Dia'),
        ('ADJUNTO', 'Adjunto'),
        ('OFICIAL_DIA', 'Oficial de Dia'),
        ('GUARDA', 'Guarda ao Quartel'),
        ('PLANTAO', 'Plantão'),
        ('PERMANENCIA', 'Permanência'),
    ]

    if not servicos.exists():
        c.drawString(50, y, "Nenhum militar escalado.")
    else:
        for tipo, titulo in sections:
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
                        c.showPage()
                        largura, altura = A4
                        y = altura - 50
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
                        y -= 28
                        c.setLineWidth(1)
                        c.line(50, y, largura - 50, y)
                        y -= 18
                        c.setFont("Helvetica", 11)
                        c.drawCentredString(largura / 2, y, f"Serviço do dia {hoje.strftime('%d/%m/%Y')}")
                        y -= 32
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(50, y, "Serviços por Tipo")
                        y -= 18
                        c.setLineWidth(0.7)
                        c.line(50, y, largura - 50, y)
                        y -= 16

            # Espaço entre seções
            y -= 10

    # 🖊️ Rodapé
    y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Sargenteação / Administração do Serviço")

    c.showPage()
    c.save()

    return response
    
@login_required
def gerar_aditamento_pdf_por_data(request, ano, mes, dia):
    if not pode_gerar_relatorios(request.user):
        return HttpResponseForbidden("Você não tem permissão para gerar o aditamento.")

    from datetime import date as _date
    try:
        data_ref = _date(year=ano, month=mes, day=dia)
    except ValueError:
        data_ref = date.today()

    servicos = Servico.objects.filter(data=data_ref).select_related('militar')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="aditamento_{data_ref.strftime("%d_%m_%Y")}.pdf"'
    )

    c = canvas.Canvas(response, pagesize=A4)
    largura, altura = A4

    y = altura - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
    y -= 28
    c.setLineWidth(1)
    c.line(50, y, largura - 50, y)
    y -= 18

    c.setFont("Helvetica", 11)
    c.drawCentredString(
        largura / 2, y,
        f"Serviço do dia {data_ref.strftime('%d/%m/%Y')}"
    )

    y -= 32

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Serviços por Tipo")
    y -= 18
    c.setLineWidth(0.7)
    c.line(50, y, largura - 50, y)
    y -= 16

    c.setFont("Helvetica", 10)

    sections = [
        ('COMANDANTE_GUARDA', 'Comandante da Guarda'),
        ('CABO_GUARDA', 'Cabo da Guarda'),
        ('CABO_DIA', 'Cabo de Dia'),
        ('ADJUNTO', 'Adjunto'),
        ('OFICIAL_DIA', 'Oficial de Dia'),
        ('GUARDA', 'Guarda ao Quartel'),
        ('PLANTAO', 'Plantão'),
        ('PERMANENCIA', 'Permanência'),
    ]

    if not servicos.exists():
        c.drawString(50, y, "Nenhum militar escalado.")
    else:
        for tipo, titulo in sections:
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

                    if y < 60:
                        c.showPage()
                        largura, altura = A4
                        y = altura - 50
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(largura / 2, y, "ADITAMENTO AO BOLETIM INTERNO")
                        y -= 28
                        c.setLineWidth(1)
                        c.line(50, y, largura - 50, y)
                        y -= 18
                        c.setFont("Helvetica", 11)
                        c.drawCentredString(largura / 2, y, f"Serviço do dia {data_ref.strftime('%d/%m/%Y')}")
                        y -= 32
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(50, y, "Serviços por Tipo")
                        y -= 18
                        c.setLineWidth(0.7)
                        c.line(50, y, largura - 50, y)
                        y -= 16

            y -= 10

    y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Sargenteação / Administração do Serviço")

    c.showPage()
    c.save()

    return response
@login_required
def historico_militar(request, militar_id):

    # 🔐 Regra de acesso
    if not pode_gerar_relatorios(request.user):
        return HttpResponseForbidden("Você não tem permissão para acessar este histórico.")

    militar = get_object_or_404(Militar, id=militar_id)

    # Filtro de mês/ano via querystring
    ano_str = request.GET.get('ano')
    mes_str = request.GET.get('mes')
    hoje = date.today()
    try:
        ano_sel = int(ano_str) if ano_str else hoje.year
        mes_sel = int(mes_str) if mes_str else hoje.month
        if not (1 <= mes_sel <= 12):
            mes_sel = hoje.month
    except ValueError:
        ano_sel = hoje.year
        mes_sel = hoje.month

    meses_pt = [
        "",
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    mes_nome = meses_pt[mes_sel]

    servicos = Servico.objects.filter(
        militar=militar
    ).order_by('-data')

    total_servicos = servicos.count()
    ultimo_servico = servicos.first()

    total_mes = servicos.filter(
        data__month=mes_sel,
        data__year=ano_sel
    ).count()

    context = {
        'militar': militar,
        'servicos': servicos,
        'total_servicos': total_servicos,
        'ultimo_servico': ultimo_servico,
        'total_mes': total_mes,
        'ano': ano_sel,
        'mes': mes_sel,
        'mes_nome': mes_nome,
    }

    return render(request, 'core/historico_militar.html', context)

@login_required
def relatorio_mensal_militar_pdf(request, militar_id, ano, mes):

    if not pode_gerar_relatorios(request.user):
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

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, 30, "Documento gerado pelo Sistema de Sargenteação")

    pdf.showPage()
    pdf.save()

    return response

@login_required
def api_efetivo(request):
    if not pode_visualizar_efetivo(request.user):
        return HttpResponseForbidden("Você não tem permissão para visualizar militares.")
    q = request.GET.get('q', '').strip()
    graduacao = request.GET.get('graduacao', '').strip()
    militares = Militar.objects.all().order_by('nome')
    if q:
        militares = militares.filter(nome__icontains=q)
    if graduacao:
        militares = militares.filter(graduacao=graduacao)
    graduacoes = Militar.GRADUACOES_CHOICES
    return render(request, 'core/api_efetivo.html', {
        'militares': militares,
        'q': q,
        'graduacao': graduacao,
        'graduacoes': graduacoes,
        'can_manage': pode_gerenciar_militares(request.user),
        'can_reports': pode_gerar_relatorios(request.user),
    })

@login_required
def api_militar_novo(request):
    if not pode_gerenciar_militares(request.user):
        return HttpResponseForbidden("Você não tem permissão para criar militares.")
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        graduacao = request.POST.get('graduacao', 'SD')
        subunidade = request.POST.get('subunidade', '').strip() or 'Geral'
        ativo = request.POST.get('ativo') == 'on'
        if nome:
            Militar.objects.create(nome=nome, graduacao=graduacao, subunidade=subunidade, ativo=ativo)
            messages.success(request, 'Militar criado com sucesso.')
        else:
            messages.error(request, 'Nome é obrigatório.')
    return redirect('api_efetivo')

@login_required
def api_militar_editar(request, militar_id):
    if not pode_gerenciar_militares(request.user):
        return HttpResponseForbidden("Você não tem permissão para editar militares.")
    militar = get_object_or_404(Militar, id=militar_id)
    if request.method == 'POST':
        militar.nome = request.POST.get('nome', militar.nome).strip()
        militar.graduacao = request.POST.get('graduacao', militar.graduacao)
        militar.subunidade = request.POST.get('subunidade', militar.subunidade).strip()
        militar.ativo = request.POST.get('ativo') == 'on'
        militar.save()
        messages.success(request, 'Militar atualizado.')
    return redirect('api_efetivo')

@login_required
def api_militar_excluir(request, militar_id):
    if not pode_gerenciar_militares(request.user):
        return HttpResponseForbidden("Você não tem permissão para excluir militares.")
    militar = get_object_or_404(Militar, id=militar_id)
    if request.method == 'POST':
        militar.delete()
        messages.success(request, 'Militar excluído.')
    return redirect('api_efetivo')

@login_required
def calendario_servicos(request):
    if not pode_visualizar_efetivo(request.user):
        return HttpResponseForbidden("Você não tem permissão para visualizar o calendário.")
    subunidades = Militar.objects.values_list('subunidade', flat=True).distinct().order_by('subunidade')
    militares = Militar.objects.filter(ativo=True).order_by('nome')
    return render(request, 'core/calendario_servicos.html', {
        'subunidades': subunidades,
        'militares': militares,
    })

@login_required
def calendario_events(request):
    if not pode_visualizar_efetivo(request.user):
        return HttpResponseForbidden("Você não tem permissão para visualizar o calendário.")
    from datetime import datetime, timedelta
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    subunidade = request.GET.get('subunidade')
    try:
        start = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else date.today()
        end = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else date.today()
    except ValueError:
        start = date.today()
        end = start
    qs_serv = Servico.objects.filter(data__gte=start, data__lte=end).select_related('militar')
    qs_afast = Afastamento.objects.filter(data_inicio__lte=end, data_fim__gte=start).select_related('militar')
    if subunidade:
        qs_serv = qs_serv.filter(militar__subunidade=subunidade)
        qs_afast = qs_afast.filter(militar__subunidade=subunidade)
    tipo_colors = {
        'COMANDANTE_GUARDA': '#795548',
        'CABO_GUARDA': '#8D6E63',
        'CABO_DIA': '#9C27B0',
        'ADJUNTO': '#3F51B5',
        'OFICIAL_DIA': '#3949AB',
        'GUARDA': '#009688',
        'PLANTAO': '#2196F3',
        'PERMANENCIA': '#607D8B',
    }
    events = []
    for s in qs_serv:
        title = s.militar.nome
        events.append({
            'id': f'srv-{s.id}',
            'title': title,
            'start': s.data.isoformat(),
            'end': (s.data + timedelta(days=1)).isoformat(),
            'allDay': True,
            'color': tipo_colors.get(s.tipo, '#1976D2'),
            'extendedProps': {
                'tipo': s.tipo,
                'militarId': s.militar.id,
            }
        })
    for a in qs_afast:
        title = a.militar.nome
        events.append({
            'id': f'af-{a.id}',
            'title': title,
            'start': a.data_inicio.isoformat(),
            'end': (a.data_fim + timedelta(days=1)).isoformat(),
            'allDay': True,
            'color': '#E53935',
            'extendedProps': {
                'tipo': 'AFASTAMENTO',
                'militarId': a.militar.id,
            }
        })
    return JsonResponse(events, safe=False)

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
    if not pode_gerenciar_usuarios(request.user):
        return HttpResponseForbidden("Você não tem permissão para gerenciar usuários.")

    from django.contrib.auth.models import User, Group
    from .utils.permissoes import get_all_groups_with_counts, get_user_role_display, assign_default_group
    if request.method == 'POST':
        novo_username = request.POST.get('novo_username', '').strip()
        graduacao = request.POST.get('graduacao', 'SD').strip()
        subunidade = request.POST.get('subunidade', 'Geral').strip()
        if novo_username:
            user, created = User.objects.get_or_create(username=novo_username)
            if created:
                user.set_unusable_password()
                user.is_active = True
                user.save()
                assign_default_group(user)
                Militar.objects.get_or_create(
                    nome=novo_username,
                    defaults={'graduacao': graduacao, 'subunidade': subunidade, 'ativo': True}
                )
                messages.success(request, f'Usuário {novo_username} criado')
            else:
                messages.info(request, f'Usuário {novo_username} já existe')

    users = User.objects.all().select_related()
    groups_data = get_all_groups_with_counts()

    # Add role display to each user
    users_with_roles = []
    for user in users:
        user_dict = {
            'user': user,
            'role': get_user_role_display(user),
            'groups': list(user.groups.values_list('name', flat=True))
        }
        users_with_roles.append(user_dict)

    context = {
        'users': users_with_roles,
        'groups': groups_data,
    }

    return render(request, 'core/admin_user_management.html', context)

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import BasePermission, IsAuthenticated
from .serializers import MilitarSerializer, AfastamentoSerializer
from .utils.permissoes import (
    pode_gerenciar_militares,
    pode_gerenciar_afastamentos,
    pode_visualizar_efetivo
)


class IsAdminOrReadOnly(BasePermission):
    """Custom permission: Admin can do anything, others can only read"""

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user.is_authenticated
        return pode_gerenciar_militares(request.user)


class CanManageMilitares(BasePermission):
    """Permission to manage military personnel (Admin only)"""

    def has_permission(self, request, view):
        return pode_gerenciar_militares(request.user)


class CanManageAfastamentos(BasePermission):
    """Permission to manage absences (Admin or Sargenteante)"""

    def has_permission(self, request, view):
        return pode_gerenciar_afastamentos(request.user)


class CanViewEfetivo(BasePermission):
    """Permission to view daily roster (All authenticated users)"""

    def has_permission(self, request, view):
        return pode_visualizar_efetivo(request.user)


class MilitarViewSet(ModelViewSet):
    queryset = Militar.objects.all()
    serializer_class = MilitarSerializer

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['list', 'retrieve']:
            # Anyone authenticated can view
            permission_classes = [IsAuthenticated]
        else:
            # Only admin can create/update/delete
            permission_classes = [CanManageMilitares]

        return [permission() for permission in permission_classes]


class AfastamentoViewSet(ModelViewSet):
    queryset = Afastamento.objects.all().select_related('militar')
    serializer_class = AfastamentoSerializer

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['list', 'retrieve']:
            # Anyone authenticated can view
            permission_classes = [IsAuthenticated]
        else:
            # Admin or Sargenteante can manage
            permission_classes = [CanManageAfastamentos]

        return [permission() for permission in permission_classes]


from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Militar, Afastamento

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def efetivo_do_dia(request):
    hoje = date.today()

    afastados_ids = Afastamento.objects.filter(
        data_inicio__lte=hoje,
        data_fim__gte=hoje
    ).values_list('militar_id', flat=True)

    militares_disponiveis = Militar.objects.filter(
        ativo=True
    ).exclude( 
    )

    data = {
        "data": hoje,
        "efetivo": [
            {
                "id": m.id,
                "nome": m.nome,
                "graduacao": m.graduacao,
                "subunidade": m.subunidade
            }
            for m in militares_disponiveis
        ]
    }

    return Response(data)
