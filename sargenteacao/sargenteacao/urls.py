from django.contrib import admin
from django.urls import path, include

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
     # 🔑 JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # sua app
    path('', core_views.home, name='home'),
    path('', include('core.urls')),
    path('api/efetivo/', core_views.api_efetivo, name='api_efetivo'),
    path('api/', include('core.urls')),  # 🔴 ISSO É O MAIS IMPORTANTE
]
