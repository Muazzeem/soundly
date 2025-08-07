import uuid

from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True


class UUIDBaseModel(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True)

    class Meta:
        abstract = True


class TimeStampModel(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveTimeStampModel(TimeStampModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class ActiveObjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
