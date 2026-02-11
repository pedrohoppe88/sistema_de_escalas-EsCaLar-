from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from core.views import MilitarViewSet, AfastamentoViewSet


router = DefaultRouter()
router.register(r'militares', MilitarViewSet, basename='militar')
router.register(r'afastamentos', AfastamentoViewSet, basename='afastamento')


urlpatterns = [
    # Views tradicionais
    path('efetivo/', views.ver_efetivo, name='ver_efetivo'),
    path('registrar-servico/', views.registrar_servico, name='registrar_servico'),
    path('aditamento/pdf/', views.gerar_aditamento_pdf, name='aditamento_pdf'),
    path('aditamento/pdf/<int:ano>/<int:mes>/<int:dia>/', views.gerar_aditamento_pdf_por_data, name='aditamento_pdf_por_data'),
    path('calendario/', views.calendario_servicos, name='calendario_servicos'),
    path('calendario/events/', views.calendario_events, name='calendario_events'),
    path('militar/novo/', views.api_militar_novo, name='api_militar_novo'),
    path('militar/<int:militar_id>/editar/', views.api_militar_editar, name='api_militar_editar'),
    path('militar/<int:militar_id>/excluir/', views.api_militar_excluir, name='api_militar_excluir'),

    path(
        'militar/<int:militar_id>/historico/',
        views.historico_militar,
        name='historico_militar'
    ),

    path(
        'militar/<int:militar_id>/relatorio/<int:ano>/<int:mes>/pdf/',
        views.relatorio_mensal_militar_pdf,
        name='relatorio_mensal_militar_pdf'
    ),

    # Autenticação
    path('login/', views.login_view, name='login'),
    path('login-modern/', views.login_moderno, name='login_moderno'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),

    # Administração
    path(
        'admin/usuarios/',
        views.admin_user_management,
        name='admin_user_management'
    ),

    # API (DRF)
    path('', include(router.urls)),
]
