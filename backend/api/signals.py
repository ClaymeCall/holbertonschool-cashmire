from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Category, DEFAULT_CATEGORIES, User


@receiver(post_save, sender=User, dispatch_uid="api.create_default_categories")
def create_default_categories(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        Category.objects.bulk_create(
            [
                Category(user=instance, name=name, description=description)
                for name, description in DEFAULT_CATEGORIES
            ]
        )
