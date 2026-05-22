from rest_framework import serializers
from core.models.member_models import Member
from core.models.subscription_models import SubscriptionPlan, MemberSubscription
from django.db import transaction
from datetime import timedelta

class MemberSerializer(serializers.ModelSerializer):
    subscription_plan = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        write_only=True,
        required=True
    )

    class Meta:
        model = Member
        fields = ['id', 'club', 'full_name', 'mobile', 'email', 'joined_at', 'is_active', 'created_at', 'subscription_plan']

    def create(self, validated_data):
        subscription_plan = validated_data.pop('subscription_plan')
        
        with transaction.atomic():
            member = Member.objects.create(**validated_data)
            
            # Create the initial subscription
            start_date = member.joined_at
            end_date = start_date + timedelta(days=subscription_plan.duration_days)
            
            MemberSubscription.objects.create(
                member=member,
                club=member.club,
                subscription_plan=subscription_plan,
                start_date=start_date,
                original_end_date=end_date,
                effective_end_date=end_date,
                status="active"
            )
            
            return member
