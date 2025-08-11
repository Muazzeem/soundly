from users.api.urls import urlpatterns as user_urls
from music.api.urls import urlpatterns as music_urls
from core.api.urls import urlpatterns as core_urls
# from subscription.api.urls import urlpatterns as subscription_urls
from notifications.urls import urlpatterns as notifications_urls

app_name = "api"

urlpatterns = [
    *user_urls,
    *music_urls,
    *core_urls,
    *notifications_urls,
]
