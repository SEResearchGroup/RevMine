from django.apps import AppConfig
import sys


class CollectorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'collectors'

    def ready(self):
        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'shell', 'test']):
            return

        from .kafka_handlers import start_kafka_consumers
        start_kafka_consumers()

