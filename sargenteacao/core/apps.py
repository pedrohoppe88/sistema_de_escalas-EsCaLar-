from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Unregister the default User admin to allow custom registration
        self.unregister_user_admin()

    def unregister_user_admin(self):
        # Unregister the default User admin to allow custom registration
        from django.contrib import admin
        from django.contrib.auth.models import User
        if User in admin.site._registry:
            admin.site.unregister(User)
