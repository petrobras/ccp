"""Background jobs.

A ``Job`` row tracks one calculation; ``run_job`` is the ``django-tasks`` task
that executes it in a worker process. Handlers register per job kind:

    @register("calculate")
    def calculate(ctx):
        ...

``ctx`` (``JobContext``) gives the handler the job, its case, progress
reporting, cancellation checks and artifact storage.
"""

import logging
import time
import traceback

from django.db import close_old_connections
from django.utils import timezone
from django_tasks import task

from ccp_web.services.units import Cancelled, InputError

from . import storage
from .models import Job

log = logging.getLogger("ccp_web.jobs")

HANDLERS = {}
QUEUES = {"monitoring": "monitoring"}


def register(kind, queue="default"):
    def decorator(func):
        HANDLERS[kind] = func
        if queue != "default":
            QUEUES[kind] = queue
        return func

    return decorator


class JobContext:
    """What a handler sees of its job."""

    PROGRESS_INTERVAL = 0.5
    CANCEL_INTERVAL = 1.0

    def __init__(self, job):
        self.job = job
        self.case = job.case
        self.params = job.params or {}
        self._last_progress = 0.0
        self._last_cancel_check = 0.0
        self._cancelled = False

    @property
    def state(self):
        return self.case.state

    def progress(self, fraction, message=""):
        """Record progress (0..1); raises ``Cancelled`` if cancel was requested."""
        now = time.monotonic()
        self.job.progress = max(0.0, min(1.0, float(fraction)))
        if message:
            self.job.message = message[:500]
        if now - self._last_progress >= self.PROGRESS_INTERVAL or fraction >= 1.0:
            self.job.heartbeat = timezone.now()
            Job.objects.filter(pk=self.job.pk).update(
                progress=self.job.progress,
                message=self.job.message,
                heartbeat=self.job.heartbeat,
            )
            self._last_progress = now
        self.check_cancelled()

    def cancelled(self):
        now = time.monotonic()
        if (
            not self._cancelled
            and now - self._last_cancel_check >= self.CANCEL_INTERVAL
        ):
            self._last_cancel_check = now
            self._cancelled = Job.objects.filter(
                pk=self.job.pk, cancel_requested=True
            ).exists()
        return self._cancelled

    def check_cancelled(self):
        if self.cancelled():
            raise Cancelled()

    def warn(self, message):
        self.job.warnings = list(self.job.warnings or []) + [message]

    def set_result(self, **values):
        self.job.result = {**(self.job.result or {}), **values}
        Job.objects.filter(pk=self.job.pk).update(
            result=self.job.result, heartbeat=timezone.now()
        )

    def secret(self, name):
        from . import secrets as secret_store

        return secret_store.take_for_job(self.job.pk, name)

    def save_artifact(self, key, name, content):
        return storage.save_artifact(self.case, key, name, content, job=self.job)

    def update_state(self, **values):
        """Merge values into the case state (e.g. a curve name after loading)."""
        from .state import update_state

        update_state(self.case, **values)

    def sleep(self, seconds):
        """Sleep in short steps so a cancel request is noticed quickly."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self._last_cancel_check = 0.0
            self.check_cancelled()
            time.sleep(min(0.5, max(0.0, end - time.monotonic())))


def start_job(case, kind, params=None, secrets=None):
    """Create a job row and enqueue its task.

    ``secrets`` ({name: value}) are handed to the worker through the cache,
    never through the job row (see ``core.secrets``).
    """
    from . import secrets as secret_store

    if kind not in HANDLERS:
        raise KeyError(f"No handler for job kind {kind!r}")
    job = Job.objects.create(
        owner=case.owner, case=case, kind=kind, params=params or {}
    )
    for name, value in (secrets or {}).items():
        secret_store.stash_for_job(job.pk, name, value)
    queue = QUEUES.get(kind, "default")
    result = run_job.using(queue_name=queue).enqueue(job.pk)
    Job.objects.filter(pk=job.pk, task_id="").update(task_id=str(result.id))
    job.refresh_from_db()
    return job


def active_jobs(case, kinds=None):
    qs = Job.objects.filter(case=case, status__in=Job.ACTIVE)
    if kinds:
        qs = qs.filter(kind__in=list(kinds))
    return qs


def cancel_job(job):
    Job.objects.filter(pk=job.pk).update(cancel_requested=True)
    if job.status == Job.PENDING:
        Job.objects.filter(pk=job.pk, status=Job.PENDING).update(
            status=Job.CANCELLED, finished=timezone.now(), message="Cancelled"
        )


def _finish(job, status, **fields):
    job.status = status
    job.finished = timezone.now()
    for k, v in fields.items():
        setattr(job, k, v)
    job.save()


@task()
def run_job(job_id):
    close_old_connections()
    try:
        job = Job.objects.select_related("case").get(pk=job_id)
    except Job.DoesNotExist:
        log.warning("Job %s vanished before it ran", job_id)
        return
    if job.status != Job.PENDING:
        return
    if job.cancel_requested:
        _finish(job, Job.CANCELLED, message="Cancelled")
        return
    handler = HANDLERS.get(job.kind)
    job.status = Job.RUNNING
    job.started = timezone.now()
    job.heartbeat = job.started
    job.save(update_fields=["status", "started", "heartbeat"])
    ctx = JobContext(job)
    try:
        handler(ctx)
    except Cancelled:
        _finish(job, Job.CANCELLED, message="Cancelled")
    except InputError as exc:
        _finish(
            job,
            Job.FAILED,
            error=str(exc),
            result={**(job.result or {}), "errors": exc.errors},
            message="Invalid input",
        )
    except Exception as exc:
        log.exception("Job %s (%s) failed", job.pk, job.kind)
        _finish(
            job,
            Job.FAILED,
            error=f"{type(exc).__name__}: {exc}",
            result={**(job.result or {}), "traceback": traceback.format_exc()[-8000:]},
            message="Failed",
        )
    else:
        job.progress = 1.0
        _finish(job, Job.SUCCEEDED, message=job.message or "Done")
    finally:
        close_old_connections()
