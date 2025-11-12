from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    """Return the value for a given key from a dictionary."""
    try:
        return d.get(key, 0)
    except AttributeError:
        return 0

@register.filter
def replace(value, args):
    old, new = args.split(',')
    return value.replace(old, new)

@register.filter
def percent(value, decimals=2):
    """Format a decimal as a percentage string with specified decimals."""
    try:
        return f"{round(value * 100, decimals)}%"
    except (TypeError, ValueError):
        return ""
