from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

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

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="likes", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'post')

class Dislike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="dislikes", on_delete=models.CASCADE)

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
    sentiment = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.author.username}"
