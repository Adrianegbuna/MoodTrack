from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View)
from .models import Post, Like, Dislike, Comment
from django.http import JsonResponse
from users.models import Follow
from .forms import CommentForm
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import FormMixin
from .ml_model import predict_sentiment



# ----------------------------
# CATEGORY POST LIST
# ----------------------------
class CategoryPostView(ListView):
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

        posts_with_sentiment = []

        for post in context["posts"]:
            comments = post.comments.all()

            total = comments.count()

            sentiment_counts = {
                "happy": 0,
                "angry": 0,
                "sad": 0,
                "fear": 0,
                "surprise": 0,
                "neutral": 0,
            }

            for comment in comments:
                if comment.sentiment in sentiment_counts:
                    sentiment_counts[comment.sentiment] += 1

            # Convert to percentages
            sentiment_percentages = {}
            for key in sentiment_counts:
                if total > 0:
                    sentiment_percentages[key] = round(
                        (sentiment_counts[key] / total) * 100
                    )
                else:
                    sentiment_percentages[key] = 0

            post.sentiment_data = sentiment_percentages
            post.total_comments = total

            posts_with_sentiment.append(post)

        context["posts"] = posts_with_sentiment
        context["current_category"] = self.kwargs.get("category")

        return context


# ----------------------------
# USER POSTS LIST + FOLLOW DATA
# ----------------------------
class UserPostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'moodtrack_app/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(User, username=self.kwargs.get('username'))

        is_following = False
        if self.request.user.is_authenticated and self.request.user != profile_user:
            is_following = Follow.objects.filter(
                follower=self.request.user,
                following=profile_user
            ).exists()

        context['profile_user'] = profile_user
        context['is_following'] = is_following
        context['followers_count'] = profile_user.followers.count()
        context['following_count'] = profile_user.following.count()
        return context


# ----------------------------
# POST DETAIL + COMMENTS
# ----------------------------
class PostDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Post
    template_name = "moodtrack_app/post_detail.html"
    context_object_name = "post"
    form_class = CommentForm

    def get_success_url(self):
        return reverse("post-detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = self.object.comments.all()
        context["form"] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = self.object
            comment.author = request.user

            sentiment = predict_sentiment(comment.content)
            comment.sentiment = sentiment
            comment.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


# ----------------------------
# CREATE / UPDATE / DELETE POSTS
# ----------------------------
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
        return self.request.user == post.author


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = reverse_lazy('home')

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author



# ----------------------------
# LIKE & DISLIKE POSTS
# ----------------------------
class LikePostView(LoginRequiredMixin, View):
    def post(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(Post, id=post_id)

        # Remove dislike if exists
        Dislike.objects.filter(user=request.user, post=post).delete()

        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()

        data = {
            "likes": post.total_likes(),
            "dislikes": post.total_dislikes(),
        }
        return JsonResponse(data)


class DislikePostView(LoginRequiredMixin, View):
    def post(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(Post, id=post_id)

        # Remove like if exists
        Like.objects.filter(user=request.user, post=post).delete()

        dislike, created = Dislike.objects.get_or_create(user=request.user, post=post)
        if not created:
            dislike.delete()

        data = {
            "likes": post.total_likes(),
            "dislikes": post.total_dislikes(),
        }
        return JsonResponse(data)

class LandingPageView(TemplateView):
    template_name = 'moodtrack_app/landingpage.html'


