import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.template.loader import render_to_string

class PostConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.post_id = self.scope['url_route']['kwargs']['post_id']
        self.room_group_name = f'post_{self.post_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket (like/dislike/comment from client)
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_post',
                'message_type': message_type,
                'data': data
            }
        )
    
    # Receive message from room group
    async def update_post(self, event):
        data = event['data']
        
        # Send to WebSocket
        await self.send(text_data=json.dumps({
            'type': event['message_type'],
            'likes': data.get('likes'),
            'dislikes': data.get('dislikes'),
            'comments_count': data.get('comments_count'),
            'new_comment_html': data.get('new_comment_html')
        }))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_group_name = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()
    
    async def disconnect(self, close_code):
        if not self.scope["user"].is_anonymous:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'type': event.get('notification_type', 'info')
        }))