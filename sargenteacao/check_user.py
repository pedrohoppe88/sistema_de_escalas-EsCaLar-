import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User

print("Checking users in database:")
users = User.objects.all()
for user in users:
    print(f"Username: {user.username}, Email: {user.email}, Active: {user.is_active}")

print("\nChecking specific user 'sd_hoppe':")
user = User.objects.filter(username='sd_hoppe').first()
if user:
    print(f"User exists: {user.username}")
    print(f"Email: {user.email}")
    print(f"Active: {user.is_active}")
    print(f"Password check for 'teste123456': {user.check_password('teste123456')}")
else:
    print("User 'sd_hoppe' does not exist")
