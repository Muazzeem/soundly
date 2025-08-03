from django.db import models


class UserTypeChoice(models.TextChoices):
    BASIC = "basic", "Basic"
    PREMIUM = "premium", "Premium"
    ARTIST = "artist", "Artist"
    INFLUENCER = "influencer", "Influencer"

