import os
import sys
from django.apps import AppConfig


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    def ready(self):
        # Prevent running during migrations, testing, shell, or other management commands
        non_worker_commands = {'makemigrations', 'migrate', 'test', 'shell', 'collectstatic'}
        if any(cmd in sys.argv for cmd in non_worker_commands):
            return

        # Check if we are running runserver and ensure we only start on the main worker process
        if 'runserver' in sys.argv:
            if os.environ.get('RUN_MAIN') != 'true':
                return

        # Start the background email worker thread
        from .email_worker import start_email_worker
        start_email_worker()

