from django.db import models
from django.utils.translation import gettext_lazy as _

from .choices import SubscriptionTypeChoice
from core.models import UUIDBaseModel, ActiveTimeStampModel
from users.models import User

class Subscription(ActiveTimeStampModel, UUIDBaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    type = models.CharField(
        _("Type"),
        max_length=10,
        choices=SubscriptionTypeChoice.choices,
        default=SubscriptionTypeChoice.MONTHLY,
    )
    start_date = models.DateTimeField(
        _("Start date"),
    )
    end_date = models.DateTimeField(
        _("End date"),
    )
    subscription_id = models.CharField(_("Subscription ID"), max_length=250)
    gateway_data = models.JSONField(_("Gateway data"))

    class Meta:
        ordering = ("-id",)

    def __str__(self):
        return self.user.email