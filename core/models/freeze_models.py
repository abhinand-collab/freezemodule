from django.db import models
from django.contrib.auth import get_user_model
from .location_models import Region, City, Club
from .member_models import Member
from .subscription_models import MemberSubscription

User = get_user_model()

class Freeze(models.Model):
    STATUS_CHOICES = (
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("completed", "Completed"),
    ("partial_failed", "Partial Failed"),
    ("failed", "Failed"),
    )

    TARGET_CHOICES = (
        ("region", "Region"),
        ("city", "City"),
        ("club", "Club"),
        ("member", "Member"),
    )
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES
    )
    status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default="pending"
    )
    task_id = models.CharField(max_length=255, null=True, blank=True)
    total_members = models.PositiveIntegerField(default=0)
    processed_members = models.PositiveIntegerField(default=0)
    error_logs = models.TextField(blank=True)
    region = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes_region"
    )
    city = models.ForeignKey(
        City,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes_city"
    )
    club = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes_club"
    )
    member = models.ForeignKey(
        Member,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes_member"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.target_type} Freeze"


class FreezeLog(models.Model):
    STATUS_CHOICES = (
        ("success", "Success"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    )

    freeze = models.ForeignKey(
        Freeze,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    member_subscription = models.ForeignKey(
        MemberSubscription,
        on_delete=models.CASCADE,
        related_name="freeze_logs"
    )

    old_end_date = models.DateField()
    new_end_date = models.DateField(
        null=True,
        blank=True
    )

    freeze_days = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    error_message = models.TextField(blank=True)

    retry_count = models.PositiveIntegerField(default=0)

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)


class SubscriptionFreezePeriod(models.Model):
    member_subscription = models.ForeignKey(
        MemberSubscription,
        on_delete=models.CASCADE,
        related_name="freeze_periods"
    )

    freeze = models.ForeignKey(
        Freeze,
        on_delete=models.CASCADE
    )

    start_date = models.DateField()
    end_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)