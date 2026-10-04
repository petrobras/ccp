"""Template helpers for state-bound inputs, result tables and Plotly charts.

The input tags read ``state`` (the case state) and ``errors`` ({key: message})
from the template context, so a page template only names the key.
"""

import json
import math

from django import template
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from ccp_web.services import gas as gas_service
from ccp_web.services import schemas

register = template.Library()


def _state(context):
    return context.get("state") or {}


def _errors(context):
    return context.get("errors") or {}


def _value(context, key):
    value = _state(context).get(key, "")
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        # number inputs: keep 0.0 readable
        return repr(value)
    return value


def _cls(context, key, base):
    return f"{base} invalid" if key in _errors(context) else base


def _title(context, key, extra=""):
    msg = _errors(context).get(key)
    return msg or extra


def _xdis(expr):
    """Alpine binding that disables the control while ``expr`` is true."""
    return format_html(' x-bind:disabled="{}"', expr) if expr else ""


@register.simple_tag(takes_context=True)
def inp(
    context,
    key,
    cls="inp",
    placeholder="",
    disabled=False,
    type="text",
    xdis="",
    **attrs,
):
    """Text input bound to ``state[key]``.

    ``xdis`` is an Alpine expression that disables the input while true.
    """
    extra = format_html_join(
        " ", '{}="{}"', ((k.replace("_", "-"), v) for k, v in attrs.items())
    )
    return format_html(
        '<input type="{}" name="{}" value="{}" class="{}" placeholder="{}" title="{}" '
        'autocomplete="off" spellcheck="false"{}{} {}>',
        type,
        key,
        _value(context, key),
        _cls(context, key, cls),
        placeholder,
        _title(context, key),
        mark_safe(" disabled" if disabled else ""),
        _xdis(xdis),
        extra,
    )


@register.simple_tag(takes_context=True)
def num(context, key, cls="inp", step="any", disabled=False, xdis="", **attrs):
    """Numeric input for ``number`` fields."""
    return inp(
        context,
        key,
        cls=cls,
        disabled=disabled,
        type="number",
        step=step,
        xdis=xdis,
        **attrs,
    )


@register.simple_tag(takes_context=True)
def sel(
    context,
    key,
    options=None,
    cls="sel",
    disabled=False,
    labels=None,
    xdis="",
    keep_current=True,
):
    """Select bound to ``state[key]``; options default to the schema's.

    A stored value missing from ``options`` is kept as an extra option unless
    ``keep_current`` is false (the browser then selects the first option).
    """
    current = _state(context).get(key, "")
    if options is None:
        app_type = context.get("app_type")
        field = schemas.get_schema(app_type).fields.get(key) if app_type else None
        options = list(field.options) if field else []
    options = list(options)
    if keep_current and current not in options and current not in ("", None):
        options = [current] + options
    labels = labels or {}
    opts = format_html_join(
        "",
        '<option value="{}"{}>{}</option>',
        (
            (
                o,
                mark_safe(" selected") if o == current else "",
                labels.get(o, o) if o != "" else "—",
            )
            for o in options
        ),
    )
    return format_html(
        '<select name="{}" class="{}" title="{}"{}{}>{}</select>',
        key,
        _cls(context, key, cls),
        _title(context, key),
        mark_safe(" disabled" if disabled else ""),
        _xdis(xdis),
        opts,
    )


@register.simple_tag(takes_context=True)
def gas_sel(context, key, cls="sel", xdis=""):
    """Select of the six gas names."""
    return sel(context, key, gas_service.gas_names(_state(context)), cls=cls, xdis=xdis)


@register.simple_tag(takes_context=True)
def chk(context, key, label="", help="", disabled=False, xmodel=""):
    """Checkbox with a hidden ``false`` so unchecking is submitted."""
    checked = bool(_state(context).get(key))
    model = format_html(' x-model="{}"', xmodel) if xmodel else ""
    return format_html(
        '<label class="chk"><input type="hidden" name="{}" value="false">'
        '<input type="checkbox" name="{}" value="true"{}{}{}><span>{}</span>{}</label>',
        key,
        key,
        mark_safe(" checked" if checked else ""),
        mark_safe(" disabled" if disabled else ""),
        model,
        label,
        help_icon(help),
    )


@register.simple_tag(name="help")
def help_icon(text):
    """Info icon whose tooltip (``data-help``) is drawn by app.js, like Streamlit's help."""
    if not text:
        return ""
    return format_html(
        '<button type="button" class="help" data-help="{}" aria-label="{}">'
        '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4">'
        '<circle cx="8" cy="8" r="6.3"/><path d="M8 7.2v4" stroke-linecap="round"/>'
        '<circle cx="8" cy="4.9" r=".45" fill="currentColor"/></svg></button>',
        text,
        text,
    )


@register.filter
def get(mapping, key):
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        try:
            return mapping[key]
        except (KeyError, IndexError, TypeError):
            return None


@register.filter
def has_key(mapping, key):
    return bool(mapping) and key in mapping


@register.simple_tag
def key(*parts):
    """Join parts into a state key: ``{% key param '_point_' i %}``."""
    return "".join(str(p) for p in parts)


@register.filter
def cell(value, column_format):
    """Format a results-table value: ``percent``, ``scientific`` or plain."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if column_format == "percent":
        return f"{value:.2%}"
    if column_format == "scientific":
        return f"{value:.4e}"
    if isinstance(value, float):
        return (
            f"{value:.5g}"
            if abs(value) < 1e-3 and value != 0
            else f"{value:,.5f}".rstrip("0").rstrip(".")
        )
    return value


@register.filter
def pct(value, digits=1):
    try:
        return f"{float(value):.{int(digits)}f}"
    except (TypeError, ValueError):
        return ""


@register.simple_tag
def plotly(figure, height=380, cls="chart-card", title=""):
    """A chart mounted client-side from JSON by ``ccpPlot``.

    ``figure`` is a plotly Figure or its JSON dict.
    """
    if figure is None:
        return ""
    if hasattr(figure, "to_plotly_json"):
        import plotly.io as pio

        data = pio.to_json(figure, validate=False)
    elif isinstance(figure, str):
        data = figure
    else:
        data = json.dumps(figure)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return format_html(
        '<div class="{}"><div class="plot" style="height:{}px" x-data '
        'x-init="ccpPlot($el)">'
        '<script type="application/json">{}</script></div></div>',
        cls,
        height,
        mark_safe(data),
    )


@register.filter
def dict_items(d):
    return list((d or {}).items())


@register.filter
def json_attr(value):
    return json.dumps(value)
