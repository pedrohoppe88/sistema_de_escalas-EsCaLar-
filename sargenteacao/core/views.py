from django.shortcuts import render
from .services import calcular_efetivo_do_dia
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
                return redirect('efetivo_do_dia')
            else:
                messages.error(request, 'Credenciais inválidas.')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

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

def logout_view(request):
    logout(request)
    messages.info(request, 'Você foi desconectado.')
    return redirect('login')


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
def historico_militar(request, militar_id):

    # 🔐 Regra de acesso
    if not pode_gerar_relatorios(request.user):
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
    from .utils.permissoes import get_all_groups_with_counts, get_user_role_display

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
        id__in=afastados_ids
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