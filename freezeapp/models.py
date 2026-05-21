from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.


class Region(models.Model):
    name = models.CharField(max_length=255, unique=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class City(models.Model):
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="cities"
    )

    name = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("region", "name")

    def __str__(self):
        return f"{self.name} - {self.region.name}"

class Club(models.Model):
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="clubs"
    )

    name = models.CharField(max_length=255)

    address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("city", "name")

    def __str__(self):
        return f"{self.name} - {self.city.name}"
    
class Member(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="members"
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    full_name = models.CharField(max_length=255)

    mobile = models.CharField(max_length=20)

    email = models.EmailField(blank=True)

    joined_at = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
    
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=255)

    duration_days = models.PositiveIntegerField()

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    is_active = models.BooleanField(default=True)

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

    # optional cached value
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
    
class Freeze(models.Model):

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

    region = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes"
    )

    city = models.ForeignKey(
        City,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes"
    )

    club = models.ForeignKey(
        Club,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes"
    )

    member = models.ForeignKey(
        Member,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="freezes"
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