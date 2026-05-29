from django.db import models
from .location_models import Region, City, Club
from .member_models import Member
from .subscription_models import MemberSubscription

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
    created_by = models.CharField(
        max_length=255,
        default="System",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.target_type} Freeze"

    @property
    def target_name(self):
        if self.target_type == 'region' and self.region:
            return self.region.name
        elif self.target_type == 'city' and self.city:
            return self.city.name
        elif self.target_type == 'club' and self.club:
            return self.club.name
        elif self.target_type == 'member' and self.member:
            return self.member.full_name
        return "Unknown"

    @property
    def display_region(self):
        if self.target_type == 'region' and self.region:
            return self.region.name
        elif self.target_type == 'city' and self.city:
            return self.city.region.name
        elif self.target_type == 'club' and self.club:
            return self.club.city.region.name
        elif self.target_type == 'member' and self.member:
            return self.member.club.city.region.name
        return None

    @property
    def display_city(self):
        if self.target_type == 'city' and self.city:
            return self.city.name
        elif self.target_type == 'club' and self.club:
            return self.club.city.name
        elif self.target_type == 'member' and self.member:
            return self.member.club.city.name
        return None

    @property
    def display_club(self):
        if self.target_type == 'club' and self.club:
            return self.club.name
        elif self.target_type == 'member' and self.member:
            return self.member.club.name
        return None


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