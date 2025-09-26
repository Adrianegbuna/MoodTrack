from django.contrib import admin
from .models import Post


@admin.register(Post)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content', 'author', 'category', 'created_at')