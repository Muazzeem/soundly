from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import PublicSubscriptionApiViewSet, StripeWebhookView

app_name = "account"


public_router = DefaultRouter()
public_router.register(
    r"subscriptions", PublicSubscriptionApiViewSet, "public_subscription_api"
)

urlpatterns = [
    path("", include(public_router.urls)),
    path("stripe-webhook/", StripeWebhookView.as_view()),
]