from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Count, Q, IntegerField, Sum, Case, When
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from calendar import month_name
from datetime import date
# Import dos modelos
from .models import Militar, Servico, Afastamento
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Import dos serviços
from .services import (
    calcular_efetivo_do_dia,
    calcular_efetivo_por_data,
    tipos_permitidos_por_graduacao,
    filtrar_militares_aptos,
    filtrar_militares_nao_aptos,
    get_opcoes_tipo_por_militar,
    get_tipos_ocupados_por_data,
    pode_atribuir_tipo,
    registrar_servicos,
    atualizar_servico,
    excluir_servico,
    adicionar_servico,
    calcular_estatisticas_servico,
    calcular_contagem_por_tipo,
    gerar_eventos_calendario,
    get_historico_servicos,
    get_estatisticas_historico,
    TIPO_SERVICO_LABELS,
    CARGOS_ESPECIAIS,
)

# Import dos formulários
from .forms import LoginForm, RegistrationForm, MilitarForm, AfastamentoForm

# Import dos serviços de PDF (com alias para evitar conflito de nomes)
from .pdf_services import gerar_aditamento_pdf as gerar_aditamento_pdf_service, gerar_relatorio_mensal_pdf

# Import das permissões
from .utils.permissoes import (
    pode_registrar_servico,
    pode_gerar_relatorios,
    pode_gerenciar_militares,
    pode_gerenciar_afastamentos,
    pode_visualizar_efetivo,
    pode_gerenciar_usuarios,
    assign_default_group
)

# Import dos serializers
from .serializers import MilitarSerializer, AfastamentoSerializer

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
            label_map = dict(Servico.TIPOS_SERVICO)
            allowed_codes = tipos_permitidos_por_graduacao(grad)
            e['opcoes_tipo'] = [(code, label_map[code]) for code in allowed_codes]
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

                #Regra 1: não duplicar serviço no mesmo dia
                if Servico.objects.filter(militar=militar, data=data_selecionada).exists():
                    continue

                # Regra 2: garantir que é apto
                if not item['apto']:
                    continue

                # Registrar serviço
                tipo = request.POST.get(f'tipo_{militar.id}', 'GUARDA')
                grad = militar.graduacao
                allowed = tipos_permitidos_por_graduacao(grad)
                if tipo not in allowed:
                    continue
                #Regra 3: cargos especiais são únicos por dia
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

        messages.success(request, 'Serviço registrado com sucesso')
        return redirect(f"{reverse('registrar_servico')}?data={data_selecionada.isoformat()}")

    especiais = {'OFICIAL_DIA', 'ADJUNTO', 'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA'}
    tipos_ocupados = list(
        Servico.objects.filter(data=data_selecionada, tipo__in=especiais).values_list('tipo', flat=True)
    )

    # Marcar se todas as opções disponíveis para o militar estão ocupadas
    for e in militares_aptos:
        codes = [code for code, _label in e.get('opcoes_tipo', [])]
        e['todos_ocupados'] = all(code in tipos_ocupados for code in codes) if codes else False

    return render(request, 'core/registrar_servico.html', {
        'militares': militares_aptos,
        'nao_aptos': militares_nao_aptos,
        'data_selecionada': data_selecionada,
        'graduacoes': Militar.GRADUACOES_CHOICES,
        'q': q,
        'graduacao': graduacao,
        'tipos_ocupados': tipos_ocupados
    })

@login_required
def editar_servicos(request):
    if not pode_registrar_servico(request.user):
        return HttpResponseForbidden("Você não tem permissão para editar serviço.")
    from datetime import datetime
    data_str = request.GET.get('data')
    try:
        data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else date.today()
    except ValueError:
        data_selecionada = date.today()
    return render(request, 'core/editar_servicos.html', {
        'data_selecionada': data_selecionada,
    })

@login_required
def editar_servico(request):
    if not pode_registrar_servico(request.user):
        return HttpResponseForbidden("Você não tem permissão para editar serviço.")
    from datetime import datetime
    from django.urls import reverse
    data_str = request.GET.get('data') if request.method == 'GET' else request.POST.get('data')
    try:
        data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else date.today()
    except ValueError:
        data_selecionada = date.today()
    if data_selecionada < date.today():
        messages.warning(request, 'Edição permitida somente para hoje e próximos dias.')
        return redirect(f"{reverse('editar_servicos')}?data={date.today().isoformat()}")
    efetivo = calcular_efetivo_por_data(data_selecionada)
    militares_aptos = [e for e in efetivo if e['apto']]
    opcoes_tipo_por_militar = {}
    label_map = dict(Servico.TIPOS_SERVICO)
    for m in Militar.objects.filter(ativo=True):
        allowed_codes = tipos_permitidos_por_graduacao(m.graduacao)
        opcoes_tipo_por_militar[m.id] = [(code, label_map[code]) for code in allowed_codes]
    servicos = Servico.objects.filter(data=data_selecionada).select_related('militar')
    especiais = {'OFICIAL_DIA', 'ADJUNTO', 'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA'}
    tipos_ocupados = set(Servico.objects.filter(data=data_selecionada, tipo__in=especiais).values_list('tipo', flat=True))
    if request.method == 'POST':
        apt_map = {e['militar'].id: e for e in militares_aptos}
        alterados = 0
        removidos = 0
        for s in servicos:
            if request.POST.get(f'delete_{s.id}') == 'on':
                s.delete()
                removidos += 1
                continue
            novo_militar_id = request.POST.get(f'militar_{s.id}', str(s.militar.id))
            novo_tipo = request.POST.get(f'tipo_{s.id}', s.tipo)
            try:
                novo_militar_id_int = int(novo_militar_id)
            except ValueError:
                novo_militar_id_int = s.militar.id
            novo_militar = get_object_or_404(Militar, id=novo_militar_id_int)
            allowed_codes = tipos_permitidos_por_graduacao(novo_militar.graduacao)
            if novo_tipo not in allowed_codes:
                messages.warning(request, 'Tipo de serviço não permitido para a graduação selecionada.')
                continue
            if novo_tipo in especiais and Servico.objects.filter(data=data_selecionada, tipo=novo_tipo).exclude(id=s.id).exists():
                messages.warning(request, 'Tipo já atribuído para a data selecionada.')
                continue
            if Servico.objects.filter(militar=novo_militar, data=data_selecionada).exclude(id=s.id).exists():
                messages.warning(request, 'Militar já possui serviço na data.')
                continue
            s.militar = novo_militar
            s.tipo = novo_tipo
            s.registrado_por = request.user
            s.save()
            alterados += 1
        if alterados and not removidos:
            messages.success(request, 'Serviços atualizados.')
        add_militar_id = request.POST.get('add_militar')
        add_tipo = request.POST.get('add_tipo')
        if add_militar_id and add_tipo:
            try:
                add_militar_int = int(add_militar_id)
                add_militar = get_object_or_404(Militar, id=add_militar_int)
                allowed_codes = tipos_permitidos_por_graduacao(add_militar.graduacao)
                if add_tipo in allowed_codes:
                    if not Servico.objects.filter(militar=add_militar, data=data_selecionada).exists():
                        if not (add_tipo in especiais and Servico.objects.filter(data=data_selecionada, tipo=add_tipo).exists()):
                            Servico.objects.create(
                                militar=add_militar,
                                data=data_selecionada,
                                tipo=add_tipo,
                                registrado_por=request.user
                            )
                            alterados += 1
                            messages.success(request, 'Serviço adicionado.')
                else:
                    messages.warning(request, 'Tipo de serviço não permitido para a graduação selecionada.')
            except ValueError:
                pass
        if alterados or removidos:
            messages.success(request, 'Alterações aplicadas.')
        return redirect(f"{reverse('editar_servico')}?data={data_selecionada.isoformat()}")
    militares_choices = Militar.objects.filter(ativo=True).order_by('nome')
    usados_ids = list(Servico.objects.filter(data=data_selecionada).values_list('militar_id', flat=True))
    militares_choices_add = Militar.objects.filter(ativo=True).exclude(id__in=usados_ids).order_by('nome')
    tipo_label_map = dict(Servico.TIPOS_SERVICO)
    tipos_lista = Servico.TIPOS_SERVICO
    servicos_info = [{'obj': s, 'opcoes': opcoes_tipo_por_militar.get(s.militar.id, [])} for s in servicos]
    return render(request, 'core/editar_servico.html', {
        'data_selecionada': data_selecionada,
        'servicos_info': servicos_info,
        'militares_choices': militares_choices,
        'militares_choices_add': militares_choices_add,
        'opcoes_tipo_por_militar': opcoes_tipo_por_militar,
        'tipo_label_map': tipo_label_map,
        'tipos_lista': tipos_lista,
        'tipos_ocupados': tipos_ocupados,
    })

@login_required
def gerar_aditamento_pdf(request):
    """Gera o PDF do aditamento do dia atual."""
    if not pode_gerar_relatorios(request.user):
        return HttpResponseForbidden("Você não tem permissão para gerar o aditamento.")

    hoje = date.today()
    servicos = Servico.objects.filter(data=hoje).select_related('militar')
    
    return gerar_aditamento_pdf_service(hoje, servicos)
    

@login_required
def gerar_aditamento_pdf_por_data(request, ano, mes, dia):
    """Gera o PDF do aditamento para uma data específica."""
    if not pode_gerar_relatorios(request.user):
        return HttpResponseForbidden("Você não tem permissão para gerar o aditamento.")

    from datetime import date as _date
    try:
        data_ref = _date(year=ano, month=mes, day=dia)
    except ValueError:
        data_ref = date.today()

    servicos = Servico.objects.filter(data=data_ref).select_related('militar')
    
    return gerar_aditamento_pdf_service(data_ref, servicos)

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
def estatisticas_servico(request):
    if not pode_gerar_relatorios(request.user):
        return HttpResponseForbidden("Você não tem permissão para ver estatísticas.")

    from datetime import datetime
    hoje = date.today()
    inicio_str = request.GET.get('inicio')
    fim_str = request.GET.get('fim')
    q = request.GET.get('q', '').strip()
    graduacao = request.GET.get('graduacao', '').strip()
    subunidade = request.GET.get('subunidade', '').strip()
    try:
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d').date() if inicio_str else hoje.replace(day=1)
    except ValueError:
        inicio = hoje.replace(day=1)
    try:
        fim = datetime.strptime(fim_str, '%Y-%m-%d').date() if fim_str else hoje
    except ValueError:
        fim = hoje

    servicos_qs = Servico.objects.filter(data__gte=inicio, data__lte=fim).select_related('militar')
    if q:
        servicos_qs = servicos_qs.filter(militar__nome__icontains=q)
    if graduacao:
        servicos_qs = servicos_qs.filter(militar__graduacao=graduacao)
    if subunidade:
        servicos_qs = servicos_qs.filter(militar__subunidade=subunidade)

    stats_qs = servicos_qs.values('militar_id').annotate(
        total=Count('id'),
        guarda=Sum(Case(When(tipo='GUARDA', then=1), default=0, output_field=IntegerField())),
        plantao=Sum(Case(When(tipo='PLANTAO', then=1), default=0, output_field=IntegerField())),
        permanencia=Sum(Case(When(tipo='PERMANENCIA', then=1), default=0, output_field=IntegerField())),
        comandante_guarda=Sum(Case(When(tipo='COMANDANTE_GUARDA', then=1), default=0, output_field=IntegerField())),
        cabo_guarda=Sum(Case(When(tipo='CABO_GUARDA', then=1), default=0, output_field=IntegerField())),
        cabo_dia=Sum(Case(When(tipo='CABO_DIA', then=1), default=0, output_field=IntegerField())),
        adjunto=Sum(Case(When(tipo='ADJUNTO', then=1), default=0, output_field=IntegerField())),
        oficial_dia=Sum(Case(When(tipo='OFICIAL_DIA', then=1), default=0, output_field=IntegerField())),
    )

    militar_ids = [row['militar_id'] for row in stats_qs]
    militares_map = {m.id: m for m in Militar.objects.filter(id__in=militar_ids)}

    stats = []
    for row in stats_qs:
        m = militares_map.get(row['militar_id'])
        if not m:
            continue
        stats.append({
            'militar': m,
            'graduacao': m.get_graduacao_display(),
            'subunidade': m.subunidade,
            'total': row['total'],
            'guarda': row['guarda'],
            'plantao': row['plantao'],
            'permanencia': row['permanencia'],
            'comandante_guarda': row['comandante_guarda'],
            'cabo_guarda': row['cabo_guarda'],
            'cabo_dia': row['cabo_dia'],
            'adjunto': row['adjunto'],
            'oficial_dia': row['oficial_dia'],
        })

    stats = sorted(stats, key=lambda x: x['total'], reverse=True)

    subunidades = Militar.objects.values_list('subunidade', flat=True).distinct().order_by('subunidade')

    tipos_order = [
        'GUARDA', 'PLANTAO', 'PERMANENCIA',
        'COMANDANTE_GUARDA', 'CABO_GUARDA', 'CABO_DIA',
        'ADJUNTO', 'OFICIAL_DIA'
    ]
    tipo_label_map = dict(Servico.TIPOS_SERVICO)
    tipo_agg = servicos_qs.values('tipo').annotate(count=Count('id'))
    tipo_count_map = {row['tipo']: row['count'] for row in tipo_agg}
    tipo_labels = [tipo_label_map[t] for t in tipos_order]
    tipo_values = [tipo_count_map.get(t, 0) for t in tipos_order]

    return render(request, 'core/estatisticas_servico.html', {
        'stats': stats,
        'inicio': inicio,
        'fim': fim,
        'q': q,
        'graduacao': graduacao,
        'subunidade': subunidade,
        'graduacoes': Militar.GRADUACOES_CHOICES,
        'subunidades': subunidades,
        'tipo_labels': tipo_labels,
        'tipo_values': tipo_values,
    })
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
