from django.contrib import admin
from .models import (
    Region, City, Club, Member, SubscriptionPlan, 
    MemberSubscription, Freeze, FreezeLog, SubscriptionFreezePeriod
)

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'is_active', 'created_at')
    list_filter = ('region', 'is_active')
    search_fields = ('name',)

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'is_active', 'created_at')
    list_filter = ('city', 'is_active')
    search_fields = ('name',)

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'club', 'mobile', 'is_active', 'joined_at')
    list_filter = ('club', 'is_active')
    search_fields = ('full_name', 'mobile', 'email')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_days', 'amount', 'is_active')
    list_filter = ('is_active',)

@admin.register(MemberSubscription)
class MemberSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('member', 'subscription_plan', 'status', 'start_date', 'original_end_date')
    list_filter = ('status', 'subscription_plan')
    search_fields = ('member__full_name',)

@admin.register(Freeze)
class FreezeAdmin(admin.ModelAdmin):
    list_display = ('target_type', 'status', 'start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('target_type', 'status', 'is_active')

@admin.register(FreezeLog)
class FreezeLogAdmin(admin.ModelAdmin):
    list_display = ('freeze', 'member_subscription', 'status', 'freeze_days', 'processed_at')
    list_filter = ('status',)
    search_fields = ('member_subscription__member__full_name',)

@admin.register(SubscriptionFreezePeriod)
class SubscriptionFreezePeriodAdmin(admin.ModelAdmin):
    list_display = ('member_subscription', 'freeze', 'start_date', 'end_date', 'created_at')
    search_fields = ('member_subscription__member__full_name',)
