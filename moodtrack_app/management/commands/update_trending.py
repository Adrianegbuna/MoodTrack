from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from moodtrack_app.models import Post

class Command(BaseCommand):
    help = 'Update trending scores for all recent posts'
    
    def handle(self, *args, **kwargs):
        posts = Post.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        )
        
        count = 0
        for post in posts:
            post.update_trending_score()
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Updated {count} posts'))