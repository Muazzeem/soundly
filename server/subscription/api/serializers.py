from rest_framework import serializers
from django.contrib.auth import get_user_model

from subscription.stripe_gateway import StripeGateway
from subscription.choices import SubscriptionTypeChoice
from subscription.models import Subscription

User = get_user_model()


class SubscriptionSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()

    def get_price(self, obj):
        gateway_data = obj.gateway_data
        if gateway_data:
            return gateway_data["data"]["object"]["amount_paid"]
        else:
            return 0

    class Meta:
        model = Subscription
        fields = (
            "id",
            "user",
            "type",
            "is_active",
            "start_date",
            "end_date",
            "subscription_id",
            "price",
        )


class SubscriptionInitSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    type = serializers.ChoiceField(choices=SubscriptionTypeChoice.choices)

    def validate_user(self, value):
        is_exists = value.subscriptions.filter(is_active=True).exists()

        if is_exists:
            raise serializers.ValidationError({
                "error": "User already has an active subscription."
            })
        return value

    def init_subscription(self):
        user = self.validated_data.get("user")
        type = self.validated_data.get("type")
        full_name = user.first_name + " " + user.last_name

        gateway = StripeGateway(
            name=full_name, email=user.email, subscription_type=type
        )
        payment_url = gateway.create_subscription()
        return payment_url
    
