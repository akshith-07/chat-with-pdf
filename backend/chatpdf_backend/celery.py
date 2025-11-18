"""
Celery configuration for async task processing
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatpdf_backend.settings')

app = Celery('chatpdf_backend')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-exports': {
        'task': 'documents.tasks.cleanup_old_exports',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
