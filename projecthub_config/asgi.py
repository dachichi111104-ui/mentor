import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projecthub_config.settings')

django_asgi_app = get_asgi_application()

try:
    import notifications.routing
    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                notifications.routing.websocket_urlpatterns
            )
        ),
    })
except Exception as e:
    print(f"ASGI WebSocket fallback to standard HTTP: {e}")
    application = django_asgi_app
