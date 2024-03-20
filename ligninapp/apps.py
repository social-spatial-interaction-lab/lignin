from django.apps import AppConfig


class LigninConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ligninapp'

    def ready(self):
        import ligninapp.signals #noqa
