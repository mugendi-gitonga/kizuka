from __future__ import absolute_import
import os
import dotenv
import sys

# 1. Load environment variables first to check the USE_PSYCOGREEN flag
# This ensures manage.py pathing doesn't break the load
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

is_worker = 'worker' in sys.argv
USE_PSYCOGREEN = os.environ.get("USE_PSYCOGREEN", "NO")

if is_worker and USE_PSYCOGREEN == "YES":
    # IMPORTANT: monkey.patch_all() must come BEFORE any other imports
    from gevent import monkey
    monkey.patch_all()
    
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()
    print("CORE: Gevent and Psycopg2 patched for high-concurrency.")

# 2. Standard Django/Celery setup
from django.conf import settings
from celery import Celery
from celery.app import trace

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

trace.LOG_SUCCESS = "Task %(name)s[%(id)s] succeeded."

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    task_queue_max_priority=10,
    timezone=settings.TIME_ZONE,
)

if os.environ.get("CELERY_RESULT_BACKEND"):
    app.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND")

app.conf.beat_schedule = {}