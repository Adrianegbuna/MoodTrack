from django import forms
from .models import Post, Comment, Report

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
    parent = forms.ModelChoiceField(
        queryset=Comment.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = Comment
        fields = ["content", "parent"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Write a comment...",
                "class": "form-control"
            })
        }

# NEW: Report Form
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['report_type', 'description']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Please describe the issue...',
                'class': 'form-control'
            })
        }