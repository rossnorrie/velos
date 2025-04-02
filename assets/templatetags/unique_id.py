# yourapp/templatetags/unique_id.py
from django import template
import uuid


register = template.Library()

@register.simple_tag
def unique_id():
    """Returns a unique hex string."""
    return uuid.uuid4().hex
