from django.urls import path, include
from rest_framework.routers import DefaultRouter
from music.api.song_statistics import song_exchange_statistics, user_summary_statistics, connected_users_list, user_statistics_by_uid, connected_users_list_by_uid
from . import views
from .views import UserReceivedSongsView

router = DefaultRouter()
router.register(r'platforms', views.MusicPlatformViewSet)
router.register(r'songs', views.SongViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('received-songs', views.ReceivedSongsMatchedView.as_view(), name='received-songs'),
    path('user-received-songs/<uuid:user_uid>/', views.UserReceivedSongsView.as_view(), name='user-received-songs'),
    path('sent-songs', views.SentSongsMatchedView.as_view(), name='sent-songs'),
    path('statistics', song_exchange_statistics, name='statistics'),
    path('user-summary', user_summary_statistics, name='user-summary'),
    path('connected-users', connected_users_list, name='connected-users'),
    path('connected-users/<uuid:user_uid>/', connected_users_list_by_uid, name='connected-users-by-uid'),
    path('user-statistics/<uuid:user_uid>/', user_statistics_by_uid, name='user-statistics-by-uid'),
    path('genre-distribution', views.GenreDistributionAPIView.as_view(), name='genre-distribution'),
]
