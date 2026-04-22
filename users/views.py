from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.generic import View, CreateView, TemplateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import Follow
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, CreateView, TemplateView
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
import json
from moodtrack_app.models import UserProfile, UserBadge, Badge, UserActivity, Comment

User = get_user_model()


class FollowUserView(LoginRequiredMixin, View):
    def post(self, request, username, *args, **kwargs):
        user_to_follow = get_object_or_404(User, username=username)
        if user_to_follow != request.user:
            Follow.objects.get_or_create(follower=request.user, following=user_to_follow)
        return redirect('user-posts', username=username)


class UnfollowUserView(LoginRequiredMixin, View):
    def post(self, request, username, *args, **kwargs):
        user_to_unfollow = get_object_or_404(User, username=username)
        Follow.objects.filter(follower=request.user, following=user_to_unfollow).delete()
        return redirect('user-posts', username=username)


class RegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(self.request, f'Your account has been created. You can now login!')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Original profile forms
        context['u_form'] = UserUpdateForm(instance=user)
        context['p_form'] = ProfileUpdateForm(instance=user.profile)
        
        # Get or create user profile for sentiment stats
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Calculate sentiment distribution from comments
        comments = Comment.objects.filter(author=user)
        total = comments.count()
        
        sentiment_dist = {}
        if total > 0:
            for emotion in ['joy', 'anger', 'sad', 'fear', 'surprise', 
                            'neutral', 'disgust', 'excitement', 'relief', 'confusion']:
                count = comments.filter(sentiment=emotion).count()
                sentiment_dist[emotion] = round((count / total) * 100, 2)
        else:
            sentiment_dist = {e: 0 for e in ['joy', 'anger', 'sad', 'fear', 'surprise', 
                           'neutral', 'disgust', 'excitement', 'relief', 'confusion']}
        
        # Calculate most expressed emotion
        most_expressed = max(sentiment_dist, key=sentiment_dist.get) if sentiment_dist else 'none'
        
        # Activity heatmap data (last year)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)
        
        activity_data = UserActivity.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).values('date').annotate(total=Count('count')).order_by('date')
        
        # Badges
        user_badges = UserBadge.objects.filter(user=user).select_related('badge')
        
        # Add all to context
        context['profile'] = profile
        context['sentiment_dist'] = json.dumps(sentiment_dist)
        context['most_expressed'] = most_expressed
        context['badges'] = user_badges
        context['next_badges'] = Badge.objects.exclude(
            id__in=user_badges.values_list('badge_id', flat=True)
        )[:3]
        context['total_comments'] = total
        
        return context
    
    def post(self, request, *args, **kwargs):
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('profile')
        
        context = self.get_context_data()
        context['u_form'] = u_form
        context['p_form'] = p_form
        return self.render_to_response(context)