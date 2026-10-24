"""Agent writes to a case's state, recorded so the user can undo them.

The agent edits the case the user has open. Each write goes through the same
coercion, normalisation and post-save hooks as a form save
(``core.state.apply_values``), and stores the values it replaced in an
``AgentRevision``. Undo puts those values back and is itself a revision, so it
can be undone too (redo). Every revision bumps ``Case.revision``, which lets
the stale-form guard (``core.state.save_post``) tell a page rendered before
the write from a current one.
"""

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.db.models import F

from ccp_web.core.models import Case
from ccp_web.core.state import ValuesError, apply_values, run_post_save_hooks
from ccp_web.services import schemas

from .models import GAS_TABLE, AgentRevision, AgentToken

# Keys that decide where a secret the browser remembers (PI password, AI API
# key) is sent. The agent never handles secrets; letting it point them at
# another host would get around that, since the user's next Run or Report
# sends the saved secret there.
AGENT_READONLY_KEYS = frozenset(
    {
        "pi_server_name",
        "pi_auth_method",
        "pi_username",
        "ai_provider",
        "ai_azure_endpoint",
        "ai_azure_deployment",
    }
)
READONLY_MESSAGE = (
    "{key} decides where a saved PI password / AI key is sent; ask the user to "
    "change it in the browser"
)


def _diff(old, new):
    """Keys whose value differs, in schema order."""
    return [k for k in new if old.get(k) != new.get(k)] + [
        k for k in old if k not in new
    ]


def check_readonly(old, new):
    """Raise ``ValuesError`` when an agent write changes a secret destination."""
    invalid = {
        k: READONLY_MESSAGE.format(key=k)
        for k in AGENT_READONLY_KEYS
        if old.get(k) != new.get(k)
    }
    if invalid:
        raise ValuesError(invalid=invalid)


def _changed_gases(table, other):
    """The gases of ``table`` that differ from ``other`` (None: not defined)."""
    table, other = table or {}, other or {}
    return {
        g: table.get(g)
        for g in sorted(set(table) | set(other))
        if table.get(g) != other.get(g)
    }


def _snapshot(state, other, keys):
    """``{key: value}`` of ``keys``; the gas table holds only changed gases.

    One gas change would otherwise record all six gases twice, and undo
    would put back gases the agent never touched.
    """
    out = {}
    for k in keys:
        value = state.get(k)
        if k == GAS_TABLE and isinstance(value, dict):
            value = _changed_gases(value, other.get(k))
        out[k] = value
    return out


def _restore(key, current, before, after):
    """The value undo writes for ``key``: ``before``, gas by gas for the table.

    For the gas table only the gases this revision changed go back (works for
    full-table snapshots of older revisions too); gases changed since by
    someone else stay as they are now.
    """
    if key != GAS_TABLE:
        return before
    table = dict(current or {})
    before, after = before or {}, after or {}
    for g in set(before) | set(after):
        if before.get(g) == after.get(g):
            continue
        if before.get(g) is None:
            table.pop(g, None)
        else:
            table[g] = before[g]
    return table


def _commit(fresh, case, new, old, keys, requested, source, note, token):
    """Save ``new`` as the state, bump the revision and record the change."""
    fresh.state = new
    fresh.revision = F("revision") + 1
    fresh.save(update_fields=["state", "revision", "updated"])
    fresh.refresh_from_db(fields=["revision"])
    revision = AgentRevision.objects.create(
        owner=fresh.owner,
        case=fresh,
        number=fresh.revision,
        source=source,
        keys=keys,
        requested=[k for k in keys if k in requested],
        before=_snapshot(old, new, keys),
        after=_snapshot(new, old, keys),
        note=note or "",
        token=token,
    )
    case.state = fresh.state
    case.revision = fresh.revision
    case.updated = fresh.updated
    return revision


def record_agent_write(
    case, values, note="", token=None, source=AgentRevision.AGENT, warnings=None
):
    """Apply agent ``values`` to the case state; return the revision or None.

    Validation errors raise ``core.state.ValuesError`` and change nothing,
    as does a change to ``AGENT_READONLY_KEYS``.
    When the values change nothing (already set), no revision is recorded
    and the case revision is not bumped. Warnings (a unit outside the page's
    options, gas fractions that add up to neither 1 nor 100) are appended to
    ``warnings`` when a list is given. ``case`` is updated in place.
    """
    with transaction.atomic():
        fresh = Case.objects.select_for_update().get(pk=case.pk)
        old = schemas.normalize(fresh.app_type, fresh.state)
        applied, found = apply_values(fresh.app_type, old, values)
        if source == AgentRevision.AGENT:
            check_readonly(old, applied)
        requested = set(_diff(old, applied))
        new = run_post_save_hooks(fresh.app_type, old, applied)
        if warnings is not None:
            warnings.extend(found)
        keys = _diff(old, new)
        if not keys:
            case.state = fresh.state
            case.revision = fresh.revision
            return None
        return _commit(fresh, case, new, old, keys, requested, source, note, token)


def undo(revision, user_or_token):
    """Put back what ``revision`` replaced; return the new (undo) revision.

    Keys the user changed since are restored anyway: undo means "put back
    what the agent replaced" (for the gas table, per gas). Undoing an undo
    is a redo. A revision can be undone once (``ValueError("already
    undone")``).

    The keys the write asked for (``requested``) go back first and the
    page's post-save hooks run on them, as when the user switches back in
    the form: undoing a switch to the orifice restores the measured flows
    from where the switch kept them, even after the orifice flows were
    stored over the test flows. The other recorded keys (what the hooks
    derived) go back only where the hooks did not set them.
    """
    if isinstance(user_or_token, AgentToken):
        token, owner = user_or_token, user_or_token.owner
    elif isinstance(user_or_token, AbstractBaseUser):
        token, owner = None, user_or_token
    else:
        raise TypeError("undo needs the user or the agent token")
    if revision.owner_id != owner.pk:
        raise PermissionError("not your revision")
    with transaction.atomic():
        fresh = Case.objects.select_for_update().get(pk=revision.case_id)
        target = AgentRevision.objects.select_for_update().get(pk=revision.pk)
        if target.undone_by_id is not None:
            raise ValueError("already undone")
        old = schemas.normalize(fresh.app_type, fresh.state)
        requested = list(target.requested or target.keys)

        def value(k):
            return _restore(k, old.get(k), target.before.get(k), target.after.get(k))

        staged = {**old, **{k: value(k) for k in requested}}
        hooked = run_post_save_hooks(fresh.app_type, old, staged)
        for k in target.keys:
            if k not in requested and hooked.get(k) == staged.get(k):
                hooked[k] = value(k)
        new = schemas.normalize(fresh.app_type, hooked)
        keys = _diff(old, new)
        result = _commit(
            fresh,
            fresh,
            new,
            old,
            keys,
            set(_diff(old, staged)),
            AgentRevision.UNDO,
            f"Undo #{target.number}" + (f": {target.note}" if target.note else ""),
            token,
        )
        target.undone_by = result
        target.save(update_fields=["undone_by"])
    revision.undone_by = result
    return result


def change_flags(rows):
    """``{pk: is_change}`` for a case's revisions ``rows``, in number order.

    A change is an agent write, or a redo (an undo of an undo, which puts
    a write back); undoing it is an "Undo". A plain undo is not a change;
    undoing it is a "Redo". Same as ``AgentRevision.is_change``, in one pass.
    """
    undoes = {r.undone_by_id: r.pk for r in rows if r.undone_by_id}
    is_change = {}
    for r in rows:
        if r.source == AgentRevision.AGENT:
            is_change[r.pk] = True
        else:
            target = undoes.get(r.pk)
            is_change[r.pk] = target is not None and not is_change.get(target, True)
    return is_change


def latest_undoable(case):
    """The newest change of the case still in effect, or None.

    A change is an agent write, or a redo (``change_flags``). Plain undos are
    skipped, so successive default undos step back through the agent's
    writes instead of redoing the last one.
    """
    rows = list(case.agent_revisions.order_by("number"))
    is_change = change_flags(rows)
    for r in reversed(rows):
        if r.undone_by_id is None and is_change[r.pk]:
            return r
    return None


def stale_keys(case, base_revision):
    """State keys agent revisions after ``base_revision`` changed."""
    keys = set()
    for row in AgentRevision.objects.filter(
        case_id=case.pk, number__gt=base_revision
    ).values_list("keys", flat=True):
        keys.update(row)
    return keys
