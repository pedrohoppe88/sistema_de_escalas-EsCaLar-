import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User
from core.utils.permissoes import assign_user_to_group, MILITAR_GROUP
from core.models import Militar

def create_test_user():
    try:
        # Criar usuário
        user = User.objects.create_user(
            username='teste_user',
            email='teste@email.com',
            password='teste123456'
        )
        assign_user_to_group(user, MILITAR_GROUP)

        # Criar perfil militar
        Militar.objects.create(
            nome='teste_user',
            graduacao='SD',
            subunidade='Teste',
            ativo=True
        )
        print('✅ Usuário criado com sucesso!')
        print('Username: teste_user')
        print('Senha: teste123456')
    except Exception as e:
        print(f'❌ Erro ao criar usuário: {str(e)}')

if __name__ == '__main__':
    create_test_user()
