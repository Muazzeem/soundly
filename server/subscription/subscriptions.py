from datetime import datetime
from django.utils.timezone import make_aware
from django.conf import settings

from decouple import config

from users.models import User
from subscription.models import Subscription
from .stripe_gateway import StripeGateway


def create_subscription(data):
    data_object = data["data"]["object"]

    email = data_object["customer_email"]
    user = User.objects.get(email=email)

    line_data = data_object["lines"]["data"][0]
    price_id = data_object["lines"]["data"][0]["pricing"]["price_details"]["price"]

    if price_id == settings.MONTHLY_PRICE_ID:
        sub_type = "monthly"
    elif price_id == settings.YEARLY_PRICE_ID:
        sub_type = "yearly"
    else:
        sub_type = "monthly"

    period_start = line_data["period"]["start"]
    period_end = line_data["period"]["end"]

    ps_native = datetime.fromtimestamp(period_start)
    ps_aware = make_aware(ps_native)

    pe_native = datetime.fromtimestamp(period_end)
    pe_aware = make_aware(pe_native)

    subscription_id = data_object["parent"]["subscription_details"]["subscription"]

    user.subscriptions.filter(is_active=True).update(is_active=False)

    Subscription.objects.create(
        user=user,
        type=sub_type,
        is_active=True,
        start_date=ps_aware,
        end_date=pe_aware,
        subscription_id=subscription_id,
        gateway_data=data,
    )


def cancel_subscription(user, subscription):
    full_name = user.first_name + " " + user.last_name
    gateway = StripeGateway(full_name, user.email, subscription.type)
    gateway.cancel_subscription(subscription.subscription_id)


def cancel_subscription_from_webhook(data):
    data_object = data["data"]["object"]
    subscription_id = data_object["id"]

    subscription = Subscription.objects.get(
        subscription_id=subscription_id, is_active=True
    )
    subscription.is_active = False
    subscription.save()