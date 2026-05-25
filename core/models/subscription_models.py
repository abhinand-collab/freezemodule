from django.db import models
from .location_models import Club
from .member_models import Member

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=255)
    duration_days = models.PositiveIntegerField()
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    is_active = models.BooleanField(default=True)
    max_freeze_days = models.PositiveIntegerField(
        default=30,
        help_text="Maximum allowed freeze duration in days for this plan"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class MemberSubscription(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE
    )
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT
    )
    start_date = models.DateField()
    original_end_date = models.DateField()
    effective_end_date = models.DateField(
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member} - {self.subscription_plan}"
