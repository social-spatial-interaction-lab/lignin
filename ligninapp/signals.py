from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LigninUser


@receiver(post_save, sender=User)
def post_save_user_signal_handler(sender, instance, created, **kwargs):
    if created:
       instance.is_staff = True
       #group = Group.objects.get(name='Group name')
       #instance.groups.add(group)
       instance.save()
       lu = LigninUser.objects.create(owner=instance)
       lu.save()