from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DocumentSequence(models.Model):
    """Next number for a document type. Locked while in use, so numbers never repeat or skip."""

    name = models.CharField(max_length=30, unique=True)
    next_value = models.PositiveBigIntegerField(default=1)

    def __str__(self):
        return f"{self.name}: {self.next_value}"
