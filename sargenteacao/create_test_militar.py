import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

from core.models import Militar

def create_test_militar():
    try:
        militar = Militar.objects.create(
            nome='João Silva',
            graduacao='SD',
            subunidade='1ª Companhia',
            ativo=True
        )
        print('✅ Militar criado com sucesso!')
        print(f'ID: {militar.id}')
        print(f'Nome: {militar.nome}')
        print(f'Graduação: {militar.get_graduacao_display()}')
    except Exception as e:
        print(f'❌ Erro ao criar militar: {str(e)}')

if __name__ == '__main__':
    create_test_militar()
