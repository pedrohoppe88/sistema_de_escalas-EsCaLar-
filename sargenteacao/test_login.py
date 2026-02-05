import os
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Militar

def test_login():
    print("🔍 Testando login...")

    # Verificar se existe usuário de teste
    try:
        user = User.objects.get(username='teste_user')
        print(f"✅ Usuário encontrado: {user.username}")
    except User.DoesNotExist:
        print("❌ Usuário 'teste_user' não encontrado. Criando...")
        user = User.objects.create_user(
            username='teste_user',
            email='teste@email.com',
            password='teste123456'
        )
        Militar.objects.create(
            nome='teste_user',
            graduacao='SD',
            subunidade='Teste',
            ativo=True
        )
        print("✅ Usuário criado!")

    # Testar login via API
    try:
        response = requests.post('http://127.0.0.1:8000/api/token/', json={
            'username': 'teste_user',
            'password': 'teste123456'
        })

        if response.status_code == 200:
            data = response.json()
            print("✅ Login via API bem-sucedido!")
            print(f"Access Token: {data.get('access')[:20]}...")
            print(f"Refresh Token: {data.get('refresh')[:20]}...")
            return data
        else:
            print(f"❌ Erro no login via API: {response.status_code}")
            print(f"Resposta: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Servidor não está rodando. Execute: python manage.py runserver")
        return None

if __name__ == '__main__':
    test_login()
