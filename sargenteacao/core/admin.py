from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Militar, Afastamento, Servico
# Unregister the default User admin before registering custom one
if User in admin.site._registry:
    admin.site.unregister(User)

# Register your models here.

@admin.register(Militar)
class MilitarAdmin(admin.ModelAdmin):
    list_display = ('nome', 'graduacao', 'subunidade', 'ativo')
    list_filter = ('graduacao', 'subunidade', 'ativo')
    search_fields = ('nome',)

@admin.register(Afastamento)
class AfastamentoAdmin(admin.ModelAdmin):
    list_display = ('militar', 'tipo', 'data_inicio', 'data_fim')
    list_filter = ('tipo',)
    search_fields = ('militar__nome',)

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('militar', 'data', 'registrado_por', 'data_registro')
    list_filter = ('data',)
    search_fields = ('militar__nome',)
    readonly_fields = ('data_registro',)

    def has_delete_permission(self, request, obj=None):
        return False  # 🔒 histórico não pode ser apagado

# Custom UserAdmin to manage permissions
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'date_joined'
    )
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'groups'
    )
    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email'
    )
    ordering = ('username',)

# Register custom User and Group admin
admin.site.register(User, CustomUserAdmin)
