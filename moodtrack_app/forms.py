from django import forms
from .models import Post

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
