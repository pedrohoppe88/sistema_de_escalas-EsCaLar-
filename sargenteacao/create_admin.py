#!/usr/bin/env python
"""
Script to create admin user for the sargenteacao system
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User, Group
from core.models import Militar

def create_admin_user():
    """Create admin user with full permissions"""

    # Create or get admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@sistema.com',
            'is_staff': True,
            'is_superuser': True
        }
    )

    # Set password
    admin_user.set_password('admin123')
    admin_user.save()

    # Assign to ADMIN group
    try:
        admin_group = Group.objects.get(name='ADMIN')
        admin_user.groups.add(admin_group)
        print("✅ Admin user assigned to ADMIN group")
    except Group.DoesNotExist:
        print("⚠️ ADMIN group not found - run setup_groups.py first")

    # Create corresponding Militar instance
    militar, militar_created = Militar.objects.get_or_create(
        nome='Administrador',
        defaults={
            'graduacao': 'CEL',
            'subunidade': 'Administração',
            'ativo': True
        }
    )

    print("✅ Admin user created successfully!")
    print(f"   Username: admin")
    print(f"   Password: admin123")
    print(f"   Email: admin@sistema.com")
    print(f"   Groups: {[g.name for g in admin_user.groups.all()]}")
    print(f"   Militar instance: {'Created' if militar_created else 'Already exists'}")

if __name__ == '__main__':
    create_admin_user()
