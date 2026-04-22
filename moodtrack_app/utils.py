from django.utils import timezone
from datetime import timedelta
from django.db.models import Count



def get_sentiment_insights(user=None, days=30):
    """Generate insights from sentiment data"""
    from_date = timezone.now() - timedelta(days=days)
    
    if user:
        comments = user.comments.filter(created_at__gte=from_date)
    else:
        from .models import Comment
        comments = Comment.objects.filter(created_at__gte=from_date)
    
    total = comments.count()
    if total == 0:
        return {"message": "No data available"}
    
    insights = {
        "total_comments": total,
        "dominant_sentiment": comments.values('sentiment').annotate(
            count=Count('id')
        ).order_by('-count').first()['sentiment'],
        "positivity_ratio": (
            comments.filter(sentiment__in=['joy', 'excitement', 'relief']).count() / total
        ) * 100,
        "activity_trend": "increasing" if total > 50 else "steady"
    }
    
    return insights

def check_and_award_badges(user):
    from .models import UserProfile, Badge, UserBadge

    profile, _ = UserProfile.objects.get_or_create(user=user)

    for badge in Badge.objects.all():
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            continue

        awarded = False

        if badge.points_required and profile.points >= badge.points_required:
            awarded = True
        elif badge.condition == 'comments_10' and profile.total_comments >= 10:
            awarded = True
        elif badge.condition == 'joy_5' and profile.joy_count >= 5:
            awarded = True

        if awarded:
            UserBadge.objects.create(user=user, badge=badge)