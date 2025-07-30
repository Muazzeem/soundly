from django.urls import path, include
from rest_framework.routers import DefaultRouter
from music.api.song_statistics import song_exchange_statistics, user_summary_statistics
from . import views

router = DefaultRouter()
router.register(r'platforms', views.MusicPlatformViewSet)
router.register(r'songs', views.SongViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('received-songs', views.SentSongsMatchedView.as_view(), name='received-songs'),
    path('statistics', song_exchange_statistics, name='statistics'),
    path('user-summary', user_summary_statistics, name='user-summary'),
    path('genre-distribution', views.GenreDistributionAPIView.as_view(), name='genre-distribution'),
]
