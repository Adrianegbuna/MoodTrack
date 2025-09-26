from django.urls import path
from .views import (
    CategoryPostView, PostDetailView, PostCreateView, PostUpdateView, PostDeleteView,
    UserPostListView,
)
from . import views

urlpatterns = [
    path('', CategoryPostView.as_view(), {"category": "all"}, name="home"),
    path('political-posts/', CategoryPostView.as_view(), {"category": "Political"}, name="political-posts"),
    path('sports-posts/', CategoryPostView.as_view(), {"category": "Sports"}, name="sports-posts"),
    path('nature-posts/', CategoryPostView.as_view(), {"category": "Nature"}, name="nature-posts"),
    path('food-posts/', CategoryPostView.as_view(), {"category": "Food"}, name="food-posts"),
    path('user/<str:username>', UserPostListView.as_view(), name='user-posts'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update', PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete', PostDeleteView.as_view(), name='post-delete'),
    path('about/', views.about, name='blog-about'),
    path('post/<int:post_id>/like/', views.like_post, name='like-post'),
    path('post/<int:post_id>/dislike/', views.dislike_post, name='dislike-post'),
]