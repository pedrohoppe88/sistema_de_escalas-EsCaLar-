import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from django.contrib.auth.models import User

def change_password():
    try:
        user = User.objects.get(username='teste_user')
        user.set_password('teste123456')
        user.save()
        print('✅ Senha alterada com sucesso!')
        print('Username: teste_user')
        print('Nova senha: teste123456')
    except User.DoesNotExist:
        print('❌ Usuário teste_user não encontrado')

if __name__ == '__main__':
    change_password()
