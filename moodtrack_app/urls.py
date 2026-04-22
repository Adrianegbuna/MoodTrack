from django.urls import path
from .views import (
    CategoryPostView, PostCreateView, PostUpdateView, PostDeleteView,
    UserPostListView, LikePostView, DislikePostView, LandingPageView,
    PostDetailView, AnalyticsView, SentimentTrendsView,
    TrendingPostsView, RandomPostView, RandomPostByCategoryView,
    CommentReplyView, ReportCreateView, ExportAnalyticsView, BadgesView
)

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing-page'),
    path('home/', CategoryPostView.as_view(), {"category": "all"}, name="home"),
    path('political-posts/', CategoryPostView.as_view(), {"category": "Political"}, name="political-posts"),
    path('sports-posts/', CategoryPostView.as_view(), {"category": "Sports"}, name="sports-posts"),
    path('nature-posts/', CategoryPostView.as_view(), {"category": "Nature"}, name="nature-posts"),
    path('food-posts/', CategoryPostView.as_view(), {"category": "Food"}, name="food-posts"),
    path('user/<str:username>', UserPostListView.as_view(), name='user-posts'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update', PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete', PostDeleteView.as_view(), name='post-delete'),
    path('post/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
    path('post/<int:post_id>/dislike/', DislikePostView.as_view(), name='dislike-post'),
    path('analytics', AnalyticsView.as_view(), name='analytics'),
    path('analytics/trends/', SentimentTrendsView.as_view(), name='sentiment-trends'),
    path('analytics/export/', ExportAnalyticsView.as_view(), name='export-analytics'),
    path('badges/', BadgesView.as_view(), name='badges'),
    path('trending/', TrendingPostsView.as_view(), name='trending'),
    path('random/', RandomPostView.as_view(), name='random-post'),
    path('random/<str:category>/', RandomPostByCategoryView.as_view(), name='random-post-category'),
    path('comment/<int:comment_id>/reply/', CommentReplyView.as_view(), name='comment-reply'),
    path('report/create/', ReportCreateView.as_view(), name='create-report'),
]
