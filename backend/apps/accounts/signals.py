from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import GuestProfile, OwnerProfile, User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.role == User.Role.GUEST:
        GuestProfile.objects.create(user=instance)
    elif instance.role == User.Role.OWNER:
        OwnerProfile.objects.create(user=instance)
