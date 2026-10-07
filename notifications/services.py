from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from notifications.models import Notification
from asgiref.sync import async_to_sync
try:
    from channels.layers import get_channel_layer
except ImportError:
    get_channel_layer = None

def notify(recipient, notification_type=None, title="", body="", message=None, link="", sender=None, dedupe_key=None, project=None):
    """
    Unified notification helper for ProjectHub AI.
    Creates Notification DB entry and triggers WebSocket group_send on transaction commit.
    """
    if not body and message:
        body = message
    if not recipient or not recipient.is_active:
        return None

    # Safe link check
    safe_link = link
    if safe_link and not safe_link.startswith('/'):
        safe_link = '/'

    # Deduplication check
    if dedupe_key:
        from django.core.cache import cache
        cache_k = f"notif_dedupe:{dedupe_key}"
        if cache.get(cache_k):
            return None
        cache.set(cache_k, True, timeout=86400)


    notif = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=body,
        link=safe_link
    )

    # Realtime WebSocket dispatch after DB transaction commit
    def send_ws():
        if get_channel_layer:
            try:
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{recipient.id}",
                        {
                            "type": "notification_message",
                            "data": {
                                "id": notif.id,
                                "title": notif.title,
                                "message": notif.message,
                                "link": notif.link,
                                "created_at": notif.created_at.strftime('%Y-%m-%d %H:%M')
                            }
                        }
                    )
            except Exception:
                pass

    transaction.on_commit(send_ws)
    return notif
