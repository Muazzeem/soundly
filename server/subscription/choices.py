from django.db import models


class SubscriptionTypeChoice(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"

