from rest_framework import serializers
from core.models.freeze_models import Freeze, FreezeLog, SubscriptionFreezePeriod

class FreezeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Freeze
        exclude = ['is_active', 'task_id', 'total_members', 'processed_members', 'error_logs', 'created_by']

class FreezeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreezeLog
        fields = '__all__'

class SubscriptionFreezePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFreezePeriod
        fields = '__all__'
