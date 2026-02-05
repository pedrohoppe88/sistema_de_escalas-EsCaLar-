from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist


# Group names constants
ADMIN_GROUP = 'ADMIN'
SARGENTEANTE_GROUP = 'SARGENTEANTE'
MILITAR_GROUP = 'MILITAR'


def get_or_create_group(group_name):
    """Get or create a group by name"""
    group, created = Group.objects.get_or_create(name=group_name)
    return group


def is_admin(user):
    """Check if user is in ADMIN group or is superuser"""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists()


def is_sargenteante(user):
    """Check if user is in SARGENTEANTE group"""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=SARGENTEANTE_GROUP).exists()


def is_militar(user):
    """Check if user is in MILITAR group"""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=MILITAR_GROUP).exists()


def pode_registrar_servico(user):
    """Permission to register services (Sargenteante or Admin)"""
    return is_admin(user) or is_sargenteante(user)


def pode_gerar_relatorios(user):
    """Permission to generate reports (Sargenteante or Admin)"""
    return is_admin(user) or is_sargenteante(user)


def pode_gerenciar_militares(user):
    """Permission to manage military personnel (Admin only)"""
    return is_admin(user)


def pode_gerenciar_afastamentos(user):
    """Permission to manage absences (Admin or Sargenteante)"""
    return is_admin(user) or is_sargenteante(user)


def pode_visualizar_efetivo(user):
    """Permission to view daily roster (All authenticated users)"""
    return user.is_authenticated


def pode_gerenciar_usuarios(user):
    """Permission to manage users and groups (Admin only)"""
    return is_admin(user)


def get_user_permissions(user):
    """Get all permissions for a user based on their groups"""
    if not user or not user.is_authenticated:
        return []

    permissions = []

    if is_admin(user):
        permissions.extend([
            'pode_registrar_servico',
            'pode_gerar_relatorios',
            'pode_gerenciar_militares',
            'pode_gerenciar_afastamentos',
            'pode_visualizar_efetivo',
            'pode_gerenciar_usuarios',
        ])
    elif is_sargenteante(user):
        permissions.extend([
            'pode_registrar_servico',
            'pode_gerar_relatorios',
            'pode_gerenciar_afastamentos',
            'pode_visualizar_efetivo',
        ])
    elif is_militar(user):
        permissions.extend([
            'pode_visualizar_efetivo',
        ])

    return permissions


def assign_default_group(user):
    """Assign default group to new user (Militar)"""
    try:
        militar_group = get_or_create_group(MILITAR_GROUP)
        user.groups.add(militar_group)
        user.save()
    except Exception as e:
        print(f"Error assigning default group to user {user.username}: {e}")


def setup_groups():
    """Setup all required groups in the system"""
    groups = [ADMIN_GROUP, SARGENTEANTE_GROUP, MILITAR_GROUP]

    for group_name in groups:
        get_or_create_group(group_name)

    print("Groups setup completed successfully!")


def get_user_role_display(user):
    """Get user role display name"""
    if is_admin(user):
        return "Administrador"
    elif is_sargenteante(user):
        return "Sargenteante"
    elif is_militar(user):
        return "Militar"
    else:
        return "Sem Grupo"


def assign_user_to_group(user, group_name):
    """Assign user to a specific group"""
    try:
        # Remove from all groups first
        user.groups.clear()

        # Add to new group
        group = get_or_create_group(group_name)
        user.groups.add(group)
        user.save()

        return True, f"Usuário {user.username} atribuído ao grupo {group_name}"

    except Exception as e:
        return False, f"Erro ao atribuir grupo: {str(e)}"


def get_group_members(group_name):
    """Get all users in a specific group"""
    try:
        group = Group.objects.get(name=group_name)
        return group.user_set.all()
    except Group.DoesNotExist:
        return []


def get_all_groups_with_counts():
    """Get all groups with user counts"""
    groups_data = []
    for group_name in [ADMIN_GROUP, SARGENTEANTE_GROUP, MILITAR_GROUP]:
        try:
            group = Group.objects.get(name=group_name)
            groups_data.append({
                'name': group_name,
                'count': group.user_set.count(),
                'group': group
            })
        except Group.DoesNotExist:
            groups_data.append({
                'name': group_name,
                'count': 0,
                'group': None
            })

    return groups_data
