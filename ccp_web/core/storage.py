"""Save and remove case files and artifacts through Django's storage API."""

from django.core.files.base import ContentFile
from django.db import transaction

from .models import Artifact, CaseFile


def _delete_file(field):
    if field and field.name:
        field.storage.delete(field.name)


@transaction.atomic
def save_case_file(case, key, kind, name, content):
    for old in CaseFile.objects.filter(case=case, key=key):
        _delete_file(old.file)
        old.delete()
    obj = CaseFile(owner=case.owner, case=case, key=key, kind=kind, name=name)
    obj.file.save(name, ContentFile(content), save=False)
    obj.save()
    return obj


def delete_case_file(case, key):
    for old in CaseFile.objects.filter(case=case, key=key):
        _delete_file(old.file)
        old.delete()


@transaction.atomic
def save_artifact(case, key, name, content, job=None):
    if isinstance(content, str):
        content = content.encode("utf-8")
    for old in Artifact.objects.filter(case=case, key=key):
        _delete_file(old.file)
        old.delete()
    obj = Artifact(
        owner=case.owner,
        case=case,
        key=key,
        name=name,
        job=job,
        sha256=Artifact.digest(content),
    )
    obj.file.save(name, ContentFile(content), save=False)
    obj.save()
    return obj


def delete_artifacts(case, keys):
    for old in Artifact.objects.filter(case=case, key__in=list(keys)):
        _delete_file(old.file)
        old.delete()


def delete_case_storage(case):
    for f in case.files.all():
        _delete_file(f.file)
    for a in case.artifacts.all():
        _delete_file(a.file)
