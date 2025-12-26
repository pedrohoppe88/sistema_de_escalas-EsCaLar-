from django.apps import AppConfig
from django.core.signals import app_ready


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Connect signal to unregister User admin after admin autodiscovery
        app_ready.connect(self.unregister_user_admin, sender=self)

    def unregister_user_admin(self, sender, **kwargs):
        # Unregister the default User admin to allow custom registration
        from django.contrib import admin
        from django.contrib.auth.models import User
        if User in admin.site._registry:
            admin.site.unregister(User)
