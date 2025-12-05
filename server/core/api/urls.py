from django.urls import path
from .views import country_list, activity_feed
from .reaction_views import (
    toggle_reaction,
    get_activity_reactions,
    add_comment,
    get_activity_comments,
    delete_comment
)

urlpatterns = [
    path('countries', country_list, name='country-list'),
    path('feed', activity_feed, name='activity-feed'),
    path('feed/<uuid:activity_id>/reactions/<str:reaction_type>/', toggle_reaction, name='toggle-reaction'),
    path('feed/<uuid:activity_id>/reactions/', get_activity_reactions, name='get-reactions'),
    path('feed/<uuid:activity_id>/comments/', add_comment, name='add-comment'),
    path('feed/<uuid:activity_id>/comments/list/', get_activity_comments, name='get-comments'),
    path('feed/comments/<uuid:comment_id>/', delete_comment, name='delete-comment'),
]
