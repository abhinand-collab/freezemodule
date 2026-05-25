from rest_framework import serializers
from core.models.subscription_models import SubscriptionPlan, MemberSubscription

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'duration_days', 'amount', 'max_freeze_days', 'is_active', 'created_at']

class MemberSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberSubscription
        fields = '__all__'
