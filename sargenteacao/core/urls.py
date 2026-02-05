from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from core.views import MilitarViewSet, AfastamentoViewSet


router = DefaultRouter()
router.register(r'militares', MilitarViewSet, basename='militar')
router.register(r'afastamentos', AfastamentoViewSet, basename='afastamento')


urlpatterns = [
    # Views tradicionais
    path('efetivo/', views.efetivo_do_dia, name='efetivo_do_dia'),
    path('registrar-servico/', views.registrar_servico, name='registrar_servico'),
    path('aditamento/pdf/', views.gerar_aditamento_pdf, name='aditamento_pdf'),

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
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Administração
    path(
        'admin/usuarios/',
        views.admin_user_management,
        name='admin_user_management'
    ),

    # API (DRF)
    path('', include(router.urls)),
]
