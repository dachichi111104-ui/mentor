from django import template
from projects.permissions import can as check_can

register = template.Library()

@register.simple_tag
def can_user(user, action, obj=None):
    """
    Template tag usage:
        {% can_user request.user 'task.delete' task as allow_delete %}
        {% if allow_delete %}...{% endif %}
    """
    return check_can(user, action, obj)
