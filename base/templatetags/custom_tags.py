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
