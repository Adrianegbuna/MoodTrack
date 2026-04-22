from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .utils import check_and_award_badges

# EXISTING POST MODEL (unchanged)
class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    CATEGORY_CHOICES = [
        ('Political', 'Political'),
        ('Nature', 'Nature'),
        ('Sports', 'Sports'),
        ('Food', 'Food'),
    ]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # NEW: For trending algorithm
    trending_score = models.FloatField(default=0.0)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("post-detail", args=[str(self.id)])
    
    def total_likes(self):
        return self.likes.count()

    def total_dislikes(self):
        return self.dislikes.count()
    
    def update_trending_score(self):
        """Calculate trending score based on engagement velocity"""
        from django.utils import timezone
        from datetime import timedelta
        
        hours_since_posted = (timezone.now() - self.created_at).total_seconds() / 3600
        
        # Engagement factors
        likes = self.total_likes()
        dislikes = self.total_dislikes()
        comments = self.comments.count()
        views = self.views_count
        
        # Weighted score (newer posts get higher weight)
        score = (likes * 2 + comments * 3 + views * 0.5 - dislikes) / (hours_since_posted + 2) ** 1.5
        self.trending_score = max(0, score)
        self.save(update_fields=['trending_score'])

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="likes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # NEW: For analytics

    class Meta:
        unique_together = ('user', 'post')

class Dislike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="dislikes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # NEW: For analytics

    class Meta:
        unique_together = ('user', 'post')

class Comment(models.Model):
    SENTIMENT_CHOICES = [
        ('joy', 'Joy'),
        ('anger', 'Anger'),
        ('sad', 'Sad'),
        ('fear', 'Fear'),
        ('surprise', 'Surprise'),
        ('neutral', 'Neutral'),
        ('disgust', 'Disgust'),
        ('excitement', 'Excitement'),
        ('relief', 'Relief'),
        ('confusion', 'Confusion'),
    ]

    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # NEW: For comment threading/replies
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_reported = models.BooleanField(default=False)  # NEW: For moderation

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author.username}"
    
    def is_reply(self):
        return self.parent is not None

# NEW MODEL: User Profile Extension for Reputation System
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_stats')
    points = models.PositiveIntegerField(default=0)
    reputation = models.PositiveIntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)
    
    # Sentiment tracking for personal profile
    total_comments = models.PositiveIntegerField(default=0)
    joy_count = models.PositiveIntegerField(default=0)
    anger_count = models.PositiveIntegerField(default=0)
    sad_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# NEW MODEL: Badges/Achievements
class Badge(models.Model):
    BADGE_TYPES = [
        ('sentiment', 'Sentiment Master'),
        ('engagement', 'Engagement'),
        ('community', 'Community'),
        ('milestone', 'Milestone'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='🏆')  # Emoji or icon class
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)
    points_required = models.PositiveIntegerField(default=0)
    condition = models.CharField(max_length=200, help_text="JSON condition or description")
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')

# NEW MODEL: Reports for Moderation
class Report(models.Model):
    REPORT_TYPES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('misinformation', 'Misinformation'),
        ('inappropriate', 'Inappropriate Content'),
        ('other', 'Other'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('reporter', 'post', 'comment')  # Prevent duplicate reports

# NEW MODEL: Daily Sentiment Analytics (for trends over time)
class DailySentiment(models.Model):
    date = models.DateField(auto_now_add=True)
    category = models.CharField(max_length=20, blank=True, null=True)  # Null for global
    joy_count = models.PositiveIntegerField(default=0)
    anger_count = models.PositiveIntegerField(default=0)
    sad_count = models.PositiveIntegerField(default=0)
    fear_count = models.PositiveIntegerField(default=0)
    surprise_count = models.PositiveIntegerField(default=0)
    neutral_count = models.PositiveIntegerField(default=0)
    disgust_count = models.PositiveIntegerField(default=0)
    excitement_count = models.PositiveIntegerField(default=0)
    relief_count = models.PositiveIntegerField(default=0)
    confusion_count = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('date', 'category')
        ordering = ['-date']

# NEW MODEL: User Activity Heatmap
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    date = models.DateField()
    activity_type = models.CharField(max_length=20, choices=[
        ('comment', 'Comment'),
        ('post', 'Post'),
        ('like', 'Like'),
        ('login', 'Login'),
    ])
    count = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = ('user', 'date', 'activity_type')

# Signals to update user profile points
@receiver(post_save, sender=Comment)
def update_user_points_comment(sender, instance, created, **kwargs):
    if created:
        profile, _ = UserProfile.objects.get_or_create(user=instance.author)
        profile.points += 5  # 5 points per comment
        profile.total_comments += 1
        
        # Update sentiment counts
        if instance.sentiment == 'joy':
            profile.joy_count += 1
        elif instance.sentiment == 'anger':
            profile.anger_count += 1
        elif instance.sentiment == 'sad':
            profile.sad_count += 1
            
        profile.save()
        check_and_award_badges(instance.author)

@receiver(post_save, sender=Post)
def update_user_points_post(sender, instance, created, **kwargs):
    if created:
        profile, _ = UserProfile.objects.get_or_create(user=instance.author)
        profile.points += 10
        profile.total_posts += 1   # 🔥 ADD THIS
        profile.save()

        check_and_award_badges(instance.author)

@receiver(post_save, sender=Like)
def update_user_points_like(sender, instance, created, **kwargs):
    if created:
        profile, _ = UserProfile.objects.get_or_create(user=instance.post.author)
        profile.points += 2  # 2 points when someone likes your post
        profile.reputation += 1
        profile.save()
        check_and_award_badges(instance.post.author)

def check_and_award_badges(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)

    for badge in Badge.objects.all():
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            continue

        awarded = False

        condition = badge.condition

        # ✅ COMMENTS badges (comments_1, comments_10, comments_50)
        if condition.startswith('comments_'):
            required = int(condition.split('_')[1])
            if profile.total_comments >= required:
                awarded = True

        # ✅ POINTS badges (points_100, points_500)
        elif condition.startswith('points_'):
            required = int(condition.split('_')[1])
            if profile.points >= required:
                awarded = True

        # ✅ JOY badges (joy_5)
        elif condition.startswith('joy_'):
            required = int(condition.split('_')[1])
            if profile.joy_count >= required:
                awarded = True

        # ✅ POSTS badges (posts_1)
        elif condition.startswith('posts_'):
            required = int(condition.split('_')[1])
            if profile.total_posts >= required:
                awarded = True

        # ✅ SPECIAL CASES
        elif condition == 'trending_post':
            if profile.trending_posts_count >= 1:
                awarded = True

        if awarded:
            UserBadge.objects.create(user=user, badge=badge)