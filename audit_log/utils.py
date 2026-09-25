from audit_log.models import ActivityLog

def log_action(user, action, entity_type, entity_id, description, request=None):
    """
    Unified Audit Logging Helper for ProjectHub AI
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
    return ActivityLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else '',
        description=description,
        ip_address=ip_address
    )
