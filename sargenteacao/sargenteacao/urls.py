from django.contrib import admin
from django.urls import path, include

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
     # 🔑 JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # sua app
    path('', include('core.urls')),
    path('api/', include('core.urls')),  # 🔴 ISSO É O MAIS IMPORTANTE
]