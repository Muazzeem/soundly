import stripe
from decouple import config
from django.conf import settings

class StripeGateway:
    def __init__(self, name, email, subscription_type):
        stripe.api_key = settings.STRIPE_API_KEY

        self.name = name
        self.email = email
        self.subscription_type = subscription_type

    def get_or_create_customer(self):
        customers = stripe.Customer.list(email=self.email, limit=1)

        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(
                email=self.email,
                name=self.name,
            )
        return customer

    def get_price_id(self):
        if self.subscription_type == "monthly":
            price_id = settings.MONTHLY_PRICE_ID
        elif self.subscription_type == "yearly":
            price_id = settings.YEARLY_PRICE_ID
        return price_id

    def create_subscription(self):
        customer = self.get_or_create_customer()
        front_host = settings.FRONTEND_BASE_URL

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer.id,
            line_items=[
                {
                    "price": self.get_price_id(),
                    "quantity": 1,
                },
            ],
            success_url=f"{front_host}"
            + "/account/orders?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=f"{front_host}" + "/account/orders",
        )

        return session.url

    def cancel_subscription(self, id):
        canceled_subscription = stripe.Subscription.delete(id)
        return canceled_subscription

