from django.contrib import admin
from .models import Post, Comment


@admin.register(Post)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content', 'author', 'category', 'created_at')

@admin.register(Comment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'content', 'sentiment', 'created_at')