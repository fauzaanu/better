from django.apps import AppConfig


class BetterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.better'

    def ready(self):
        """Import signal handlers when the app is ready"""
        import apps.better.models  # This will register the signal handlers
