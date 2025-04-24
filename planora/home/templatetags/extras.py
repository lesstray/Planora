from django import template


register = template.Library()


@register.filter
def dict_get(dct, key):
    try:
        return dct.get(key)
    except Exception:
        return None


@register.filter
def split(value, delimiter):
    return value.split(delimiter)
