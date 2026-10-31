from django.db import transaction

from .models import DocumentSequence


@transaction.atomic
def next_value(name):
    """Take the next number for a sequence.

    The row stays locked until the caller's transaction ends. If that transaction
    rolls back the number is returned too, so invoice numbers have no gaps.
    """
    sequence, _ = DocumentSequence.objects.select_for_update().get_or_create(name=name)
    value = sequence.next_value
    sequence.next_value = value + 1
    sequence.save(update_fields=["next_value"])
    return value
