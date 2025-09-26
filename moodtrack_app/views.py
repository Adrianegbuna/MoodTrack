from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic import (ListView, DetailView, CreateView, UpdateView,
                                  DeleteView, TemplateView)
from .models import Post, Like, Dislike
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse



class CategoryPostView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'moodtrack_app/home.html'
    context_object_name = "posts"
    paginate_by = 3

    def get_queryset(self):
        category = self.kwargs.get("category")
        if category == "all":
            return Post.objects.all().order_by("-created_at")
        return Post.objects.filter(category__iexact=category).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_category"] = self.kwargs.get("category")
        return context

class UserPostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'moodtrack_app/user_posts.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    paginate_by = 3

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-created_at')

class PostDetailView(DetailView):
    model = Post

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['category', 'title', 'content']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False  

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'
    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False  

def about(request):
    return render(request, 'moodtrack_app/about.html', {'title': 'About'})

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Remove dislike if exists
    Dislike.objects.filter(user=request.user, post=post).delete()

    # Toggle like
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()

    data = {
        'likes': post.total_likes(),
        'dislikes': post.total_dislikes(),
    }
    return JsonResponse(data)

@login_required
def dislike_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Remove like if exists
    Like.objects.filter(user=request.user, post=post).delete()

    # Toggle dislike
    dislike, created = Dislike.objects.get_or_create(user=request.user, post=post)
    if not created:
        dislike.delete()

    data = {
        'likes': post.total_likes(),
        'dislikes': post.total_dislikes(),
    }
    return JsonResponse(data)

