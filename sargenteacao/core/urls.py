from django.urls import path
from . import views

urlpatterns = [
    path('efetivo/', views.efetivo_do_dia, name='efetivo_do_dia'),
    path('registrar-servico/', views.registrar_servico, name='registrar_servico'),
    path('aditamento/pdf/', views.gerar_aditamento_pdf, name='aditamento_pdf'),
    path('militar/<int:militar_id>/historico/', views.historico_militar, name='historico_militar'),
    path(
    'militar/<int:militar_id>/relatorio/<int:ano>/<int:mes>/pdf/',
    views.relatorio_mensal_militar_pdf,
    name='relatorio_mensal_militar_pdf'
),
    path('admin/usuarios/', views.admin_user_management, name='admin_user_management'),
]
