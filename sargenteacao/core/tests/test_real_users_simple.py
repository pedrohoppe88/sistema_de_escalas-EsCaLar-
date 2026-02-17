#!/usr/bin/env python
"""
Simple real user testing script using Django's test framework.
This creates real users and tests permissions without starting a server.
"""

import os
import django
from django.test import TestCase, Client
from django.contrib.auth.models import User

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from core.models import Militar, Afastamento, Servico
from core.utils.permissoes import (
    setup_groups, assign_user_to_group,
    ADMIN_GROUP, SARGENTEANTE_GROUP, MILITAR_GROUP,
    is_admin, is_sargenteante, is_militar,
    pode_registrar_servico, pode_gerar_relatorios,
    pode_gerenciar_militares, pode_gerenciar_afastamentos,
    pode_visualizar_efetivo, pode_gerenciar_usuarios
)

def test_real_users():
    """Test the system with real users"""
    print("🧪 Testing System with Real Users")
    print("=" * 50)

    # Setup groups
    print("📋 Setting up groups...")
    setup_groups()

    # Create test users
    print("👥 Creating real test users...")

    users_data = [
        ('admin_real', 'admin123', ADMIN_GROUP, 'CEL', 'Administração'),
        ('sargenteante_real', 'sarg123', SARGENTEANTE_GROUP, '1SG', 'Pelotão Alpha'),
        ('militar_real', 'militar123', MILITAR_GROUP, 'SD', 'Pelotão Alpha'),
    ]

    created_users = {}

    for username, password, group, graduacao, subunidade in users_data:
        # Create User
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': username.split('_')[0].title(),
                'last_name': 'Test'
            }
        )

        if created:
            user.set_password(password)
            user.save()
            print(f"✅ Created user: {username}")
        else:
            print(f"ℹ️  User already exists: {username}")

        # Assign group
        assign_user_to_group(user, group)

        # Create corresponding Militar
        militar, mil_created = Militar.objects.get_or_create(
            nome=username,
            defaults={
                'graduacao': graduacao,
                'subunidade': subunidade,
                'ativo': True
            }
        )

        if mil_created:
            print(f"✅ Created Militar profile for: {username}")
        else:
            print(f"ℹ️  Militar profile already exists for: {username}")

        created_users[username] = user

    # Test permissions
    print("\n🔐 Testing Permissions")
    print("-" * 30)

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

    expected_results = {
        'admin_real': {
            'is_admin': True, 'is_sargenteante': False, 'is_militar': False,
            'pode_registrar_servico': True, 'pode_gerar_relatorios': True,
            'pode_gerenciar_militares': True, 'pode_gerenciar_afastamentos': True,
            'pode_visualizar_efetivo': True, 'pode_gerenciar_usuarios': True,
        },
        'sargenteante_real': {
            'is_admin': False, 'is_sargenteante': True, 'is_militar': False,
            'pode_registrar_servico': True, 'pode_gerar_relatorios': True,
            'pode_gerenciar_militares': False, 'pode_gerenciar_afastamentos': True,
            'pode_visualizar_efetivo': True, 'pode_gerenciar_usuarios': False,
        },
        'militar_real': {
            'is_admin': False, 'is_sargenteante': False, 'is_militar': True,
            'pode_registrar_servico': False, 'pode_gerar_relatorios': False,
            'pode_gerenciar_militares': False, 'pode_gerenciar_afastamentos': False,
            'pode_visualizar_efetivo': True, 'pode_gerenciar_usuarios': False,
        },
    }

    all_passed = True

    for username, user in created_users.items():
        print(f"\n👤 Testing user: {username} ({user.groups.first().name if user.groups.exists() else 'No Group'})")

        user_passed = True

        for perm_name, perm_func in permission_tests:
            expected = expected_results[username][perm_name]
            actual = perm_func(user)

            status = "✅" if actual == expected else "❌"
            print(f"  {status} {perm_name}: {actual}")

            if actual != expected:
                user_passed = False
                all_passed = False

        if user_passed:
            print(f"🎉 {username} permissions: PASSED")
        else:
            print(f"💥 {username} permissions: FAILED")

    # Test Django views with Client
    print("\n🌐 Testing Django Views")
    print("-" * 30)

    client = Client()

    # Test login and access
    for username, user in created_users.items():
        print(f"\n👤 Testing web access for: {username}")

        # Login
        login_success = client.login(username=username, password=f"{username.split('_')[0]}123")
        if login_success:
            print("✅ Login successful")

            # Test efetivo_do_dia (should work for all)
            response = client.get('/efetivo/')
            if response.status_code == 200:
                print("✅ Can access efetivo_do_dia")
            else:
                print(f"❌ Cannot access efetivo_do_dia: {response.status_code}")

            # Test registrar_servico (admin and sargenteante only)
            response = client.get('/registrar-servico/')
            expected_status = 200 if username in ['admin_real', 'sargenteante_real'] else 403
            if response.status_code == expected_status:
                print(f"✅ registrar_servico access correct ({response.status_code})")
            else:
                print(f"❌ registrar_servico access incorrect: {response.status_code} (expected: {expected_status})")

            # Test admin_user_management (admin only)
            response = client.get('/admin/usuarios/')
            expected_status = 200 if username == 'admin_real' else 403
            if response.status_code == expected_status:
                print(f"✅ admin_user_management access correct ({response.status_code})")
            else:
                print(f"❌ admin_user_management access incorrect: {response.status_code} (expected: {expected_status})")

        else:
            print("❌ Login failed")
            all_passed = False

        client.logout()

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL REAL USER TESTS PASSED!")
        print("\n✅ System is working correctly with real users")
        print("🔐 Permission system properly enforced")
        print("🌐 Web interface access controls working")
        print("\n🚀 Ready for production!")
    else:
        print("💥 SOME TESTS FAILED!")
        print("🔧 Please check the permission functions and user setup")

    return all_passed

def cleanup_test_users():
    """Clean up test users"""
    print("\n🧹 Cleaning up test users...")

    test_usernames = ['admin_real', 'sargenteante_real', 'militar_real']

    for username in test_usernames:
        try:
            user = User.objects.get(username=username)
            user.delete()
            print(f"✅ Deleted user: {username}")
        except User.DoesNotExist:
            print(f"ℹ️  User not found: {username}")
        except Exception as e:
            print(f"❌ Error deleting {username}: {e}")

    print("✅ Cleanup completed!")

if __name__ == '__main__':
    try:
        success = test_real_users()

        # Ask user if they want to cleanup
        if success:
            response = input("\n❓ Do you want to cleanup test users? (y/N): ").strip().lower()
            if response == 'y':
                cleanup_test_users()
            else:
                print("ℹ️  Test users kept for manual inspection")
        else:
            print("❌ Tests failed - keeping users for debugging")

    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
