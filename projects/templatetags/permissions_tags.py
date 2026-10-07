from django import template
from projects.permissions import can as check_can

register = template.Library()

@register.filter(name='can')
def can_filter(user, args):
    """
    Template filter usage:
        {% if request.user|can:"task.delete:task" %}
        or helper
        {% if request.user|can:"project.edit:project" %}
    """
    if not user:
        return False
    if ':' in args:
        action, obj_name = args.split(':', 1)
    else:
        action = args
        obj_name = None
    return check_can(user, action, obj_name)

@register.simple_tag
def can_user(user, action, obj=None):
    """
    Template tag usage:
        {% can_user request.user 'task.delete' task as allow_delete %}
        {% if allow_delete %}...{% endif %}
    """
    return check_can(user, action, obj)
