"""Agent access to the open case: tokens, write history and notes.

An AI coding agent edits the case the user has open. Every write is recorded
as an ``AgentRevision`` with the values it replaced, so the user can undo it
from the browser; the agent talks back through ``AgentNote`` rows. The agent
authenticates with an ``AgentToken`` (bearer token), never with the session:
the desktop server logs every browser request in automatically.
"""

import hashlib
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from ccp_web.core.models import Case, OwnedQuerySet

TOKEN_PREFIX = "ccpa_"
# ``last_used`` is a hint for the token list, not an audit log: skip the
# write on most requests of a busy agent.
LAST_USED_RESOLUTION = timedelta(minutes=1)


GAS_TABLE = "gas_compositions_table"


def display_value(value):
    """A recorded value as the page shows it: JSON, whole floats as integers.

    Matches the toast (agent.js ``fmt``), so the drawer and the toast show the
    same text; None and "" give None (shown as a dash).
    """
    if value is None or value == "":
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (dict, list, bool)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def _gas_summary(gas):
    """``"methane 0.9, ethane 0.1"``: the components with a nonzero fraction."""
    if not isinstance(gas, dict):
        return gas
    parts = []
    for key, value in gas.items():
        if key.startswith("molar_fraction_") and value not in (None, "", 0):
            component = gas.get("component_" + key.removeprefix("molar_fraction_"))
            parts.append(f"{component} {display_value(value)}")
    return ", ".join(parts) or "defined"


def gas_table_changes(before, after):
    """``[(label, old, new)]``, one per changed field of the changed gases.

    ``("gas_0 molar_fraction_0", 0.4, 0.5)``; a gas added or removed is one
    row with its nonzero components. Mirrors ``gasChanges`` in agent.js.
    """
    before = before if isinstance(before, dict) else {}
    after = after if isinstance(after, dict) else {}
    rows = []
    for g in sorted(set(before) | set(after)):
        old, new = before.get(g), after.get(g)
        if old == new:
            continue
        if not isinstance(old, dict) or not isinstance(new, dict):
            rows.append((g, _gas_summary(old), _gas_summary(new)))
            continue
        fields = list(new) + [k for k in old if k not in new]
        rows.extend(
            (f"{g} {k}", old.get(k), new.get(k))
            for k in fields
            if old.get(k) != new.get(k)
        )
    return rows


def token_digest(plaintext):
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class AgentToken(models.Model):
    """A bearer token for the agent API; only its SHA-256 digest is stored."""

    READ = "read"
    WRITE = "write"
    SCOPES = [(READ, "Read"), (WRITE, "Read and write")]
    DESKTOP = "desktop"
    PERSONAL = "personal"
    KINDS = [(DESKTOP, "Desktop session"), (PERSONAL, "Personal")]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_tokens"
    )
    name = models.CharField(max_length=80)
    prefix = models.CharField(max_length=12, db_index=True)
    digest = models.CharField(max_length=64, unique=True)
    scope = models.CharField(max_length=10, choices=SCOPES, default=WRITE)
    kind = models.CharField(max_length=10, choices=KINDS, default=PERSONAL)
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires = models.DateTimeField(null=True, blank=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.name} ({self.prefix}…)"

    @property
    def can_write(self):
        return self.scope == self.WRITE

    @property
    def is_expired(self):
        return self.expires is not None and self.expires <= timezone.now()

    @classmethod
    def issue(cls, owner, name, scope=WRITE, kind=PERSONAL, expires=None):
        """Create a token; return ``(row, plaintext)``. The plaintext is not kept."""
        plaintext = TOKEN_PREFIX + secrets.token_urlsafe(32)
        row = cls.objects.create(
            owner=owner,
            name=(name or "agent").strip()[:80] or "agent",
            prefix=plaintext[:12],
            digest=token_digest(plaintext),
            scope=scope,
            kind=kind,
            expires=expires,
        )
        return row, plaintext

    @classmethod
    def authenticate(cls, plaintext):
        """The live token row for ``plaintext``, or None.

        The lookup is by digest, so no plaintext comparison happens (and none
        can leak timing). Expired tokens and inactive owners are rejected.
        """
        if not plaintext or not plaintext.startswith(TOKEN_PREFIX):
            return None
        row = (
            cls.objects.select_related("owner")
            .filter(digest=token_digest(plaintext))
            .first()
        )
        if row is None or row.is_expired or not row.owner.is_active:
            return None
        now = timezone.now()
        if row.last_used is None or now - row.last_used >= LAST_USED_RESOLUTION:
            cls.objects.filter(pk=row.pk).update(last_used=now)
            row.last_used = now
        return row


class AgentRevision(models.Model):
    """One agent write (or undo) to a case's state: what it replaced and why.

    ``number`` is the case's ``revision`` after this write. ``before`` and
    ``after`` hold only the changed keys, including the ones normalisation
    changed as a consequence (gas names, flow method switch); for the gas
    table, only the gases that changed. ``requested`` are the keys the write
    itself changed, before the page's post-save hooks: undo puts those back
    and lets the hooks derive the rest again, as a form save would.
    """

    AGENT = "agent"
    UNDO = "undo"
    SOURCES = [(AGENT, "Agent"), (UNDO, "Undo")]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="agent_revisions"
    )
    number = models.PositiveIntegerField()
    source = models.CharField(max_length=10, choices=SOURCES, default=AGENT)
    keys = models.JSONField(default=list)
    requested = models.JSONField(default=list, blank=True)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    note = models.TextField(blank=True)
    undone_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="undid",
    )
    token = models.ForeignKey(
        AgentToken, null=True, blank=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "number"], name="unique_agent_revision_number"
            )
        ]

    def __str__(self):
        return f"{self.case_id}#{self.number} ({self.source})"

    @property
    def author(self):
        if self.token_id:
            return self.token.name
        return "Agent" if self.source == self.AGENT else "You"

    def changes(self):
        """``[(key, old, new)]`` in the order the keys were recorded."""
        return [(k, self.before.get(k), self.after.get(k)) for k in self.keys]

    def display_changes(self):
        """``[(label, old, new)]`` as text for the drawer, the gas table by field."""
        rows = []
        for k, old, new in self.changes():
            if k == GAS_TABLE and (isinstance(old, dict) or isinstance(new, dict)):
                rows.extend(gas_table_changes(old, new))
            else:
                rows.append((k, old, new))
        return [(k, display_value(old), display_value(new)) for k, old, new in rows]

    def is_change(self):
        """True for an agent write or a redo (an undo of an undo).

        Undoing a change takes it back out ("Undo"); undoing anything else
        (a plain undo) puts the change back ("Redo").
        """
        flag, rev = True, self
        while rev.source == self.UNDO:
            rev = rev.undid.first()
            if rev is None:
                return False
            flag = not flag
        return flag

    def as_dict(self):
        undoes = self.undid.values_list("pk", flat=True).first()
        return {
            "id": self.pk,
            "case": self.case_id,
            "number": self.number,
            "source": self.source,
            "keys": list(self.keys),
            "changed": {k: [old, new] for k, old, new in self.changes()},
            "note": self.note,
            "author": self.author,
            "undone": self.undone_by_id is not None,
            "undone_by": self.undone_by_id,
            "undoes": undoes,
            "redo": self.source == self.UNDO and self.is_change(),
            "created": self.created.isoformat() if self.created else None,
        }


class AgentNote(models.Model):
    """A message from the agent to the user, shown as plain text in the page."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="agent_notes")
    body = models.TextField()
    author = models.CharField(max_length=80, default="Agent")
    created = models.DateTimeField(auto_now_add=True)
    dismissed = models.BooleanField(default=False)

    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["-created", "-pk"]

    def __str__(self):
        return f"{self.author}: {self.body[:40]}"

    def as_dict(self):
        return {
            "id": self.pk,
            "case": self.case_id,
            "body": self.body,
            "author": self.author,
            "created": self.created.isoformat() if self.created else None,
            "dismissed": self.dismissed,
        }
