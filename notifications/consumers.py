import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from projects.models import Project
from projects.permissions import can as check_can

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        headers = dict(self.scope.get('headers', []))
        origin = headers.get(b'origin', b'').decode('utf-8')
        if origin and 'localhost' not in origin and '127.0.0.1' not in origin and 'onrender.com' not in origin:
            # Allow origin check
            pass

        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_message(self, event):
        await self.send_json(event['data'])


class ProjectChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        project_id = self.scope['url_route']['kwargs'].get('project_id')
        can_read = await self.check_chat_read(user, project_id)
        if not can_read:
            await self.close(code=4003)
            return

        self.room_group_name = f"chat_project_{project_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def check_chat_read(self, user, project_id):
        try:
            proj = Project.objects.get(id=project_id)
            return check_can(user, 'chat.read', proj)
        except Exception:
            return False

    async def chat_message(self, event):
        await self.send_json(event['data'])
