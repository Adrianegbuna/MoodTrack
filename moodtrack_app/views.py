import json
import csv
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View)
from .models import (Post, Like, Dislike, Comment, UserProfile, Badge, UserBadge, 
    Report, DailySentiment, UserActivity)
from django.http import JsonResponse, HttpResponse
from users.models import Follow
from .forms import CommentForm, ReportForm
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import FormMixin
from .ml_model import predict_sentiment
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string

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
                "joy": 0,
                "anger": 0,
                "sad": 0,
                "fear": 0,
                "surprise": 0,
                "neutral": 0,
                "disgust": 0,
                "excitement": 0,
                "relief": 0,
                "confusion": 0,
            }
            for comment in comments:
                if comment.sentiment in sentiment_counts:
                    sentiment_counts[comment.sentiment] += 1
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

class LikePostView(LoginRequiredMixin, View):
    def post(self, request, post_id, *args, **kwargs):
        post = get_object_or_404(Post, id=post_id)
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

class AnalyticsView(ListView):
    model = Post
    template_name = 'moodtrack_app/analytics.html'
    context_object_name = 'posts'
    paginate_by = 5
    def get_queryset(self):
        return Post.objects.annotate(
            joy_count=Count('comments', filter=Q(comments__sentiment='joy')),
            anger_count=Count('comments', filter=Q(comments__sentiment='anger')),
            sad_count=Count('comments', filter=Q(comments__sentiment='sad')),
            fear_count=Count('comments', filter=Q(comments__sentiment='fear')),
            surprise_count=Count('comments', filter=Q(comments__sentiment='surprise')),
            neutral_count=Count('comments', filter=Q(comments__sentiment='neutral')),
            disgust_count=Count('comments', filter=Q(comments__sentiment='disgust')),
            excitement_count=Count('comments', filter=Q(comments__sentiment='excitement')),
            relief_count=Count('comments', filter=Q(comments__sentiment='relief')),
            confusion_count=Count('comments', filter=Q(comments__sentiment='confusion')),
            total_comments=Count('comments'),
        )
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        def add_sentiment_data(posts_list):
            for post in posts_list:
                total = post.total_comments or 1
                post.sentiment_data = {
                    'joy': round(post.joy_count / total * 100),
                    'anger': round(post.anger_count / total * 100),
                    'sad': round(post.sad_count / total * 100),
                    'fear': round(post.fear_count / total * 100),
                    'surprise': round(post.surprise_count / total * 100),
                    'neutral': round(post.neutral_count / total * 100),
                    'disgust': round(post.disgust_count / total * 100),
                    'excitement': round(post.excitement_count / total * 100),
                    'relief': round(post.relief_count / total * 100),
                    'confusion': round(post.confusion_count / total * 100),
                }
            return posts_list
        add_sentiment_data(context["posts"])
        qs = self.get_queryset()
        context['top_joy_posts'] = add_sentiment_data(list(qs.order_by('-joy_count')[:5]))
        context['top_anger_posts'] = add_sentiment_data(list(qs.order_by('-anger_count')[:5]))
        context['top_sad_posts'] = add_sentiment_data(list(qs.order_by('-sad_count')[:5]))
        context['top_fear_posts'] = add_sentiment_data(list(qs.order_by('-fear_count')[:5]))
        context['top_surprise_posts'] = add_sentiment_data(list(qs.order_by('-surprise_count')[:5]))
        context['top_disgust_posts'] = add_sentiment_data(list(qs.order_by('-disgust_count')[:5]))
        context['top_confusion_posts'] = add_sentiment_data(list(qs.order_by('-confusion_count')[:5]))
        context['top_excitement_posts'] = add_sentiment_data(list(qs.order_by('-excitement_count')[:5]))
        context['top_relief_posts'] = add_sentiment_data(list(qs.order_by('-relief_count')[:5]))
        context['top_neutral_posts'] = add_sentiment_data(list(qs.order_by('-neutral_count')[:5]))
        context['controversial_posts'] = add_sentiment_data(list(qs.order_by('-total_comments')[:5]))
        return context

class SentimentTrendsView(LoginRequiredMixin, TemplateView):
    template_name = 'moodtrack_app/sentiment_trends.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        days = int(self.request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        daily_data = DailySentiment.objects.filter(
            date__range=[start_date, end_date],
            category__isnull=True
        ).order_by('date')
        dates = [d.date.strftime('%Y-%m-%d') for d in daily_data]
        emotions = ['joy', 'anger', 'sad', 'fear', 'surprise', 
                   'neutral', 'disgust', 'excitement', 'relief', 'confusion']
        datasets = {}
        for emotion in emotions:
            datasets[emotion] = [getattr(d, f'{emotion}_count') for d in daily_data]
        context['dates'] = json.dumps(dates)
        context['datasets'] = json.dumps(datasets)
        context['days'] = days
        categories = ['Political', 'Nature', 'Sports', 'Food']
        category_data = {}
        for cat in categories:
            cat_stats = DailySentiment.objects.filter(
                date__range=[start_date, end_date],
                category=cat
            ).aggregate(
                joy=Count('joy_count'),
                anger=Count('anger_count'),
                sad=Count('sad_count')
            )
            category_data[cat] = cat_stats
        context['category_data'] = json.dumps(category_data)
        return context

class TrendingPostsView(ListView):
    model = Post
    template_name = 'moodtrack_app/trending.html'
    context_object_name = 'posts'
    paginate_by = 10
    def get_queryset(self):
        recent_posts = Post.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        )
        for post in recent_posts:
            post.update_trending_score()
        timeframe = self.request.GET.get('timeframe', 'today')
        if timeframe == 'today':
            date_filter = timezone.now() - timedelta(days=1)
        elif timeframe == 'week':
            date_filter = timezone.now() - timedelta(days=7)
        elif timeframe == 'month':
            date_filter = timezone.now() - timedelta(days=30)
        else:
            date_filter = timezone.now() - timedelta(days=1)
        return Post.objects.filter(
            created_at__gte=date_filter
        ).order_by('-trending_score')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeframe'] = self.request.GET.get('timeframe', 'today')
        for post in context['posts']:
            comments = post.comments.all()
            total = comments.count()
            if total > 0:
                joy_pct = (comments.filter(sentiment='joy').count() / total) * 100
                post.dominant_sentiment = 'joy' if joy_pct > 50 else 'mixed'
            else:
                post.dominant_sentiment = 'neutral'
        return context

class RandomPostView(View):
    def get(self, request, *args, **kwargs):
        post = Post.objects.order_by('?').first()
        if post:
            return redirect('post-detail', pk=post.pk)
        return redirect('home')

class RandomPostByCategoryView(View):
    def get(self, request, category, *args, **kwargs):
        post = Post.objects.filter(category__iexact=category).order_by('?').first()
        if post:
            return redirect('post-detail', pk=post.pk)
        return redirect('home')

class CommentReplyView(LoginRequiredMixin, View):
    def post(self, request, comment_id, *args, **kwargs):
        parent_comment = get_object_or_404(Comment, id=comment_id)
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = parent_comment.post
            reply.author = request.user
            reply.parent = parent_comment
            from .ml_model import predict_sentiment
            sentiment = predict_sentiment(reply.content)
            reply.sentiment = sentiment
            reply.save()
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                from django.template.loader import render_to_string
                channel_layer = get_channel_layer()
                html = render_to_string('moodtrack_app/comment_reply.html', {'reply': reply})
                async_to_sync(channel_layer.group_send)(
                    f"post_{parent_comment.post.id}",
                    {
                        'type': 'update_post',
                        'message_type': 'new_reply',
                        'data': {
                            'parent_id': comment_id,
                            'reply_html': html
                        }
                    }
                )
            except:
                pass
            return redirect('post-detail', pk=parent_comment.post.id)
        return redirect('post-detail', pk=parent_comment.post.id)

class ReportCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            post_id = request.POST.get('post_id')
            comment_id = request.POST.get('comment_id')
            if post_id:
                report.post = get_object_or_404(Post, id=post_id)
            elif comment_id:
                report.comment = get_object_or_404(Comment, id=comment_id)
                report.comment.is_reported = True
                report.comment.save()
            report.save()
            return JsonResponse({'success': True, 'message': 'Report submitted successfully'})
        return JsonResponse({'success': False, 'errors': form.errors})

class ExportAnalyticsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('type', 'csv')
        data_type = request.GET.get('data', 'sentiment')
        if export_type == 'csv':
            return self.export_csv(data_type)
        elif export_type == 'json':
            return self.export_json(data_type)
        return HttpResponse("Invalid export type", status=400)
    def export_csv(self, data_type):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export.csv"'
        writer = csv.writer(response)
        if data_type == 'sentiment':
            writer.writerow(['Date', 'Joy', 'Anger', 'Sad', 'Fear', 'Surprise', 
                           'Neutral', 'Disgust', 'Excitement', 'Relief', 'Confusion'])
            data = DailySentiment.objects.all().order_by('-date')
            for entry in data:
                writer.writerow([
                    entry.date, entry.joy_count, entry.anger_count, entry.sad_count,
                    entry.fear_count, entry.surprise_count, entry.neutral_count,
                    entry.disgust_count, entry.excitement_count, entry.relief_count,
                    entry.confusion_count
                ])
        elif data_type == 'user_activity':
            writer.writerow(['User', 'Date', 'Activity Type', 'Count'])
            activities = UserActivity.objects.all().order_by('-date')
            for activity in activities:
                writer.writerow([
                    activity.user.username, activity.date, 
                    activity.activity_type, activity.count
                ])
        return response
    def export_json(self, data_type):
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export.json"'
        if data_type == 'sentiment':
            data = list(DailySentiment.objects.values().order_by('-date'))
        elif data_type == 'user_activity':
            data = list(UserActivity.objects.values('user__username', 'date', 
                                                   'activity_type', 'count').order_by('-date'))
        response.write(json.dumps(data, cls=DjangoJSONEncoder))
        return response

class BadgesView(LoginRequiredMixin, ListView):
    model = Badge
    template_name = 'moodtrack_app/badges.html'
    context_object_name = 'badges'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_badge_ids = UserBadge.objects.filter(user=user).values_list('badge_id', flat=True)
        context['earned_badges'] = Badge.objects.filter(id__in=user_badge_ids)
        context['unearned_badges'] = Badge.objects.exclude(id__in=user_badge_ids)
        context['user_points'] = user.profile_stats.points if hasattr(user, 'profile_stats') else 0
        return context

class PostDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Post
    template_name = "moodtrack_app/post_detail.html"
    context_object_name = "post"
    form_class = CommentForm
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.views_count += 1
        self.object.save(update_fields=['views_count'])
        UserActivity.objects.get_or_create(
            user=request.user,
            date=timezone.now().date(),
            activity_type='login'
        )
        return super().get(request, *args, **kwargs)
    def get_success_url(self):
        return reverse("post-detail", kwargs={"pk": self.object.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = self.object.comments.filter(parent__isnull=True)
        context["form"] = self.get_form()
        context['report_form'] = ReportForm()
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
            UserActivity.objects.get_or_create(
                user=request.user,
                date=timezone.now().date(),
                activity_type='comment'
            )
            self.update_daily_sentiment(sentiment, self.object.category)
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"post_{self.object.id}",
                    {
                        'type': 'update_post',
                        'message_type': 'new_comment',
                        'data': {
                            'comments_count': self.object.comments.count(),
                        }
                    }
                )
            except:
                pass
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    def update_daily_sentiment(self, sentiment, category):
        today = timezone.now().date()
        global_stats, _ = DailySentiment.objects.get_or_create(
            date=today,
            category=None
        )
        setattr(global_stats, f'{sentiment}_count', 
                getattr(global_stats, f'{sentiment}_count', 0) + 1)
        global_stats.total_comments += 1
        global_stats.save()
        if category:
            cat_stats, _ = DailySentiment.objects.get_or_create(
                date=today,
                category=category
            )
            setattr(cat_stats, f'{sentiment}_count', 
                    getattr(cat_stats, f'{sentiment}_count', 0) + 1)
            cat_stats.total_comments += 1
            cat_stats.save()        