from django import template
import os


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


@register.filter
def basename(value):
    """
    Возвращает имя файла без пути.
    Usage: {{ some_path|basename }}
    """
    return os.path.basename(value)
