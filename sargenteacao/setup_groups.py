#!/usr/bin/env python
"""
Setup script for creating user groups and permissions.
Run this script to initialize the groups in your Django project.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from core.utils.permissoes import setup_groups

def main():
    """Main setup function"""
    print("🚀 Setting up user groups and permissions...")
    print("=" * 50)

    try:
        setup_groups()
        print("✅ Groups setup completed successfully!")
        print("\n📋 Created groups:")
        print("   • ADMIN - Full system access")
        print("   • SARGENTEANTE - Service management and reports")
        print("   • MILITAR - Basic access (default for new users)")
        print("\n🔐 Permission matrix:")
        print("   ADMIN: CRUD Military, CRUD Absences, Service Registration, Reports, User Management")
        print("   SARGENTEANTE: CRUD Absences, Service Registration, Reports")
        print("   MILITAR: View Daily Roster")
        print("\n💡 Next steps:")
        print("   1. Create an admin user: python manage.py createsuperuser")
        print("   2. Assign admin group to superuser via admin panel or shell")
        print("   3. Test permissions with different user roles")

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
