import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from core.models import Militar

def test_login_simple():
    print("🔍 Testando login simples...")

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

    # Testar autenticação Django
    authenticated_user = authenticate(username='teste_user', password='teste123456')
    if authenticated_user:
        print("✅ Autenticação Django bem-sucedida!")
        print(f"Usuário: {authenticated_user.username}")
        print(f"Email: {authenticated_user.email}")
        print(f"ID: {authenticated_user.id}")
        return True
    else:
        print("❌ Falha na autenticação Django")
        return False

if __name__ == '__main__':
    test_login_simple()
