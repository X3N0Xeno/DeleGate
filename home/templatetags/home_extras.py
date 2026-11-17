import re

from django import template

register = template.Library()

_GATE_PREFIX = re.compile(r'^\s*gate\s*\d+\s*[:\-–—]\s*', re.IGNORECASE)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def gate_title(name):
    """'Gate 2: Engine & API' -> 'Engine & API'. The gate number is shown separately."""
    stripped = _GATE_PREFIX.sub('', name or '')
    return stripped or name


@register.filter
def minus_one(value):
    try:
        return int(value) - 1
    except (TypeError, ValueError):
        return value
