from django import forms
from .models import Post, Comment

CATEGORY_CHOICES = [
    ('Political', 'Political'),
    ('Nature', 'Nature'),
    ('Sports', 'Sports'),
    ('Food', 'Food'),
]

class PostForm(forms.ModelForm):
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    class Meta:
        model = Post
        fields = ["category", "title", "content"]

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Write a comment...",
                "class": "form-control"
            })
        }
