#!/usr/bin/env python
"""
Test script for permissions system.
Run this to verify that the permission system is working correctly.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User
from core.utils.permissoes import (
    is_admin, is_sargenteante, is_militar,
    pode_registrar_servico, pode_gerar_relatorios,
    pode_gerenciar_militares, pode_gerenciar_afastamentos,
    pode_visualizar_efetivo, pode_gerenciar_usuarios,
    get_user_permissions, assign_user_to_group,
    ADMIN_GROUP, SARGENTEANTE_GROUP, MILITAR_GROUP
)

def create_test_users():
    """Create test users for each role"""
    users = {}

    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin_test',
        defaults={'email': 'admin@test.com'}
    )
    if created:
        admin_user.set_password('test123')
        admin_user.save()
    assign_user_to_group(admin_user, ADMIN_GROUP)
    users['admin'] = admin_user

    # Create sargenteante user
    sarg_user, created = User.objects.get_or_create(
        username='sargenteante_test',
        defaults={'email': 'sargenteante@test.com'}
    )
    if created:
        sarg_user.set_password('test123')
        sarg_user.save()
    assign_user_to_group(sarg_user, SARGENTEANTE_GROUP)
    users['sargenteante'] = sarg_user

    # Create militar user
    militar_user, created = User.objects.get_or_create(
        username='militar_test',
        defaults={'email': 'militar@test.com'}
    )
    if created:
        militar_user.set_password('test123')
        militar_user.save()
    assign_user_to_group(militar_user, MILITAR_GROUP)
    users['militar'] = militar_user

    return users

def test_permissions():
    """Test all permissions for each user type"""
    print("🧪 Testing Permissions System")
    print("=" * 50)

    # Create test users
    users = create_test_users()

    # Define permission tests
    permission_tests = [
        ('is_admin', is_admin),
        ('is_sargenteante', is_sargenteante),
        ('is_militar', is_militar),
        ('pode_registrar_servico', pode_registrar_servico),
        ('pode_gerar_relatorios', pode_gerar_relatorios),
        ('pode_gerenciar_militares', pode_gerenciar_militares),
        ('pode_gerenciar_afastamentos', pode_gerenciar_afastamentos),
        ('pode_visualizar_efetivo', pode_visualizar_efetivo),
        ('pode_gerenciar_usuarios', pode_gerenciar_usuarios),
    ]

    # Expected results for each user type
    expected_results = {
        'admin': {
            'is_admin': True, 'is_sargenteante': False, 'is_militar': False,
            'pode_registrar_servico': True, 'pode_gerar_relatorios': True,
            'pode_gerenciar_militares': True, 'pode_gerenciar_afastamentos': True,
            'pode_visualizar_efetivo': True, 'pode_gerenciar_usuarios': True,
        },
        'sargenteante': {
            'is_admin': False, 'is_sargenteante': True, 'is_militar': False,
            'pode_registrar_servico': True, 'pode_gerar_relatorios': True,
            'pode_gerenciar_militares': False, 'pode_gerenciar_afastamentos': True,
            'pode_visualizar_efetivo': True, 'pode_gerenciar_usuarios': False,
        },
        'militar': {
            'is_admin': False, 'is_sargenteante': False, 'is_militar': True,
            'pode_registrar_servico': False, 'pode_gerar_relatorios': False,
            'pode_gerenciar_militares': False, 'pode_gerenciar_afastamentos': False,
            'pode_visualizar_efetivo': True, 'pode_gerenciar_usuarios': False,
        },
    }

    all_passed = True

    for user_type, user in users.items():
        print(f"\n👤 Testing {user_type.upper()} user: {user.username}")
        print("-" * 30)

        user_passed = True

        for perm_name, perm_func in permission_tests:
            expected = expected_results[user_type][perm_name]
            actual = perm_func(user)

            status = "✅" if actual == expected else "❌"
            print(f"  {status} {perm_name}: {actual} (expected: {expected})")

            if actual != expected:
                user_passed = False
                all_passed = False

        # Test get_user_permissions
        user_perms = get_user_permissions(user)
        expected_perms = [k for k, v in expected_results[user_type].items() if v and k.startswith('pode_')]
        perms_match = set(user_perms) == set(expected_perms)

        status = "✅" if perms_match else "❌"
        print(f"  {status} get_user_permissions: {len(user_perms)} permissions")
        if not perms_match:
            print(f"    Expected: {expected_perms}")
            print(f"    Got: {user_perms}")
            user_passed = False
            all_passed = False

        if user_passed:
            print(f"🎉 {user_type.upper()} tests PASSED")
        else:
            print(f"💥 {user_type.upper()} tests FAILED")

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL PERMISSION TESTS PASSED!")
        print("\n📋 Permission system is working correctly.")
        print("🔐 Role-based access control has been successfully implemented.")
    else:
        print("💥 SOME TESTS FAILED!")
        print("🔧 Please check the permission functions and group assignments.")

    return all_passed

if __name__ == '__main__':
    test_permissions()
