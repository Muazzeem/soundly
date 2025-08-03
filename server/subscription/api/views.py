
import json
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.views import APIView

from subscription.models import Subscription


from .serializers import *
from subscription.subscriptions import cancel_subscription, create_subscription


# Create your views here.
class PublicSubscriptionApiViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user

        if user.is_anonymous == False:
            return user.subscriptions.all()
        return Subscription.objects.none()

    @action(
        detail=False,
        methods=["post"], url_path="cancel-subscription",
        permission_classes=(IsAuthenticated,),
        serializer_class=SubscriptionInitSerializer,
    )
    def cancel_subscription(self, request):
        user = request.user
        subscription = user.subscriptions.filter(is_active=True).last()
        cancel_subscription(user, subscription)

        return Response({}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"], url_path="init-subscription",
        permission_classes=(IsAuthenticated,),
        serializer_class=SubscriptionInitSerializer,
    )
    def init_subscription(self, request):
        """
        {
            "type": monthly/yearly,
        }
        """
        data = request.data
        user = request.user
        data["user"] = user.id
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            payment_url = serializer.init_subscription()
            return Response({"payment_url": payment_url}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class StripeWebhookView(APIView):
    def post(self, request):
        data = json.loads(request.body)

        if data["type"] == "invoice.payment_succeeded":
            print(data)
            create_subscription(data)

        if data["type"] == "customer.subscription.deleted":
            pass
        return Response({}, status=status.HTTP_200_OK)