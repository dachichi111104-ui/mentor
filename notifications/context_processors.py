from notifications.models import Notification

def notification_context(request):
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False)
        recent_notifications = Notification.objects.filter(recipient=request.user)[:5]
        return {
            'unread_notifications_count': unread_notifications.count(),
            'recent_notifications': recent_notifications
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': []
    }
