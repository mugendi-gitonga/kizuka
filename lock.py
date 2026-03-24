import logging
from django.conf import settings
from django.core.cache import caches
from datetime import datetime
from celery import Task
from django_redis import get_redis_connection


logger = logging.getLogger(__name__)

alias = getattr(settings, "CELERY_TASK_LOCK_CACHE", "default")


class TaskWithLock(Task):
    """
    Base task with lock to prevent multiple execution of tasks with ETA.
    It's happens with multiple workers for tasks with any delay (countdown, ETA).
    You may override cache backend by setting `CELERY_TASK_LOCK_CACHE` in your Django settings file.
    You may override lock TTL by setting `CELERY_TASK_LOCK_EXPIRY` (seconds) in your Django settings file.
    """

    abstract = True
    lock_expiration = getattr(
        settings, "CELERY_TASK_LOCK_EXPIRY", 60 * 30
    )  # default 30 minutes
    _redis_client = None

    @property
    def redis(self):
        """
        Shared Redis client instance for this process.
        Bypasses the Django Cache wrapper to avoid overhead.
        """
        if TaskWithLock._redis_client is None:
            # This is only called ONCE per worker process/thread-start
            TaskWithLock._redis_client = get_redis_connection(alias)
        return TaskWithLock._redis_client

    @property
    def lock_key(self):
        """Unique string for task as lock key"""
        return "%s_%s" % (self.__class__.__name__, self.request.id)

    def acquire_lock(self):
        """Set lock"""
        result = self.redis.set(
            self.lock_key, "locked", ex=self.lock_expiration, nx=True
        )
        logger.info(
            "Lock for %s at %s %s",
            self.request.id,
            datetime.now(),
            "succeed" if result else "failed",
        )
        return result

    def release_lock(self):
        """Release lock"""
        result = self.redis.delete(self.lock_key)
        logger.info(
            "Lock release for %s at %s %s",
            self.request.id,
            datetime.now(),
            "succeed" if result else "failed",
        )
        return result

    def retry(self, *args, **kwargs):
        """We need to release our lock to let the first process take current task in execution on retry"""
        logger.info("Retry requested %s, %s", args, kwargs)
        self.release_lock()
        return super(TaskWithLock, self).retry(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """Checking for lock existence"""
        from celery.exceptions import Retry

        if self.acquire_lock():
            logger.info("Task %s execution with lock started", self.request.id)
            try:
                return super(TaskWithLock, self).__call__(*args, **kwargs)
            except Retry:
                # Lock already released inside self.retry(); do not double-release.
                raise
            finally:
                # Releases lock on normal completion or unhandled exception.
                # No-op (harmless) if retry() already deleted the key.
                self.release_lock()
        logger.info("Task %s skipped due lock detection", self.request.id)
