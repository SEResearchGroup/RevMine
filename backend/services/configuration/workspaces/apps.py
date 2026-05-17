from django.apps import AppConfig
import sys


class WorkspacesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workspaces'

    def ready(self):
        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'shell', 'test']):
            return
        if 'pytest' in sys.modules or any('pytest' in arg for arg in sys.argv):
            return

        # Import lazily to avoid circular imports at module load time.
        from workspaces.infrastructure.messaging.kafka_handlers import (
            start_kafka_consumers,
        )
        start_kafka_consumers()
