import os
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User

print("Criando usuário 'sd_hoppe'...")
try:
    user = User.objects.create_user('sd_hoppe', 'sd_hoppe@example.com', 'teste123456')
    user.save()
    print("✅ Usuário criado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao criar usuário: {e}")

print("\nTestando endpoint /api/token/...")
try:
    response = requests.post(
        'http://127.0.0.1:8000/api/token/',
        json={
            "username": "sd_hoppe",
            "password": "teste123456"
        }
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Token obtido com sucesso!")
        print(f"Access Token: {data.get('access')[:50]}...")
        print(f"Refresh Token: {data.get('refresh')[:50]}...")
    else:
        print(f"❌ Erro: {response.text}")

except Exception as e:
    print(f"❌ Erro na requisição: {e}")
