"""Persistence for the ccp web application.

Every row has an owner. Views reach rows only through ``for_user`` so the
desktop profile (one implicit user) and the hosted profile (many users) share
the same code paths.
"""

import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class OwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        if user is None or not user.is_authenticated:
            return self.none()
        return self.filter(owner=user)


class Project(models.Model):
    """A workspace grouping cases, typically one machine or one test campaign."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Case(models.Model):
    """One session of one page type: the equivalent of a Streamlit ``.ccp`` file.

    ``state`` holds the validated form state using the flat key names of the
    Streamlit ``session_state.json`` (see ``ccp_web.core.schemas``).
    """

    STRAIGHT_THROUGH = "straight_through"
    BACK_TO_BACK = "back_to_back"
    CURVES_CONVERSION = "curves_conversion"
    PERFORMANCE_EVALUATION = "performance_evaluation"
    CURVES_DIGITIZER = "curves_digitizer"
    APP_TYPES = [
        (STRAIGHT_THROUGH, "Straight-through"),
        (BACK_TO_BACK, "Back-to-back"),
        (CURVES_DIGITIZER, "Curves digitizer"),
        (CURVES_CONVERSION, "Curves conversion"),
        (PERFORMANCE_EVALUATION, "Performance evaluation"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cases"
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="cases")
    app_type = models.CharField(max_length=40, choices=APP_TYPES)
    name = models.CharField(max_length=200)
    state = models.JSONField(default=dict)
    state_version = models.PositiveIntegerField(default=1)
    source_version = models.CharField(
        max_length=40, blank=True, help_text="ccp version of the imported .ccp file"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return f"{self.name} ({self.get_app_type_display()})"

    def get_absolute_url(self):
        route = {
            self.STRAIGHT_THROUGH: "performance_test:case",
            self.BACK_TO_BACK: "performance_test:case",
            self.CURVES_CONVERSION: "curves:case",
            self.PERFORMANCE_EVALUATION: "evaluation:case",
            self.CURVES_DIGITIZER: "digitizer:case",
        }[self.app_type]
        return reverse(route, args=[self.pk])

    def artifact(self, key):
        return self.artifacts.filter(key=key).order_by("-created").first()

    def file(self, key):
        return self.files.filter(key=key).order_by("-created").first()


def _case_upload_to(instance, filename):
    return f"cases/{instance.case_id}/files/{uuid.uuid4().hex}/{filename}"


def _artifact_upload_to(instance, filename):
    return f"cases/{instance.case_id}/artifacts/{uuid.uuid4().hex}/{filename}"


class CaseFile(models.Model):
    """A file uploaded as case input: curve images, Engauge CSVs, curve PDFs.

    ``key`` is the legacy session key (``fig_head``, ``fig_head_sec1``,
    ``curves_file_1_case_A``); ``name`` keeps the original file name, which
    ``Impeller.load_from_engauge_csv`` needs.
    """

    CURVE_IMAGE = "curve_image"
    ENGAUGE_CSV = "engauge_csv"
    PLANT_DATA = "plant_data"
    CURVE_PDF = "curve_pdf"
    KINDS = [
        (CURVE_IMAGE, "Curve image"),
        (ENGAUGE_CSV, "Engauge CSV"),
        (PLANT_DATA, "Plant data"),
        (CURVE_PDF, "Curve PDF"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="files")
    key = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=KINDS)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=_case_upload_to, max_length=500)
    created = models.DateTimeField(auto_now_add=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["case", "key"], name="unique_case_file_key")
        ]

    def read(self):
        with self.file.open("rb") as f:
            return f.read()


class Artifact(models.Model):
    """A result produced by a calculation (TOML, zip, JSON, parquet, HTML)."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="artifacts")
    job = models.ForeignKey(
        "Job",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="artifacts",
    )
    key = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=_artifact_upload_to, max_length=500)
    sha256 = models.CharField(max_length=64)
    created = models.DateTimeField(auto_now_add=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "key"], name="unique_case_artifact_key"
            )
        ]

    def read(self):
        with self.file.open("rb") as f:
            return f.read()

    def read_text(self):
        return self.read().decode("utf-8")

    @staticmethod
    def digest(content):
        return hashlib.sha256(content).hexdigest()


class Job(models.Model):
    """A background calculation with status and progress, polled by the page."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUSES = [
        (PENDING, "Pending"),
        (RUNNING, "Running"),
        (SUCCEEDED, "Succeeded"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    ]
    ACTIVE = (PENDING, RUNNING)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="jobs")
    kind = models.CharField(max_length=40)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default=PENDING)
    progress = models.FloatField(default=0.0)
    message = models.CharField(max_length=500, blank=True)
    error = models.TextField(blank=True)
    warnings = models.JSONField(default=list, blank=True)
    result = models.JSONField(default=dict, blank=True)
    cancel_requested = models.BooleanField(default=False)
    task_id = models.CharField(max_length=64, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)
    heartbeat = models.DateTimeField(null=True, blank=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.kind} #{self.pk} ({self.status})"

    @property
    def is_active(self):
        return self.status in self.ACTIVE

    @property
    def progress_percent(self):
        return round(100 * max(0.0, min(1.0, self.progress)))

    @property
    def duration(self):
        if not self.started:
            return None
        end = self.finished or timezone.now()
        return (end - self.started).total_seconds()
