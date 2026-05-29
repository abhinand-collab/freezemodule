from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models.subscription_models import MemberSubscription
from core.services.freeze_service import apply_existing_freezes_to_subscription

@receiver(post_save, sender=MemberSubscription)
def handle_new_subscription_freezes(sender, instance, created, **kwargs):
    if created and instance.status == 'active':
        # Apply any existing location-based freezes that overlap with this new subscription
        print("----checkworking----")       
        apply_existing_freezes_to_subscription(instance)
