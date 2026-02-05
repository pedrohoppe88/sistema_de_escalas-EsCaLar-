import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sargenteacao.settings')
django.setup()

try:
    from core.views import MilitarViewSet
    print("MilitarViewSet imported successfully")
    viewset = MilitarViewSet()
    print(f"Queryset count: {viewset.queryset.count()}")
    print(f"Queryset: {list(viewset.queryset.values())}")
except Exception as e:
    print(f"Error importing MilitarViewSet: {e}")
