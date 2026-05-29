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
    club_name = serializers.CharField(source='club.name', read_only=True)
    city_name = serializers.CharField(source='club.city.name', read_only=True)
    region_name = serializers.CharField(source='club.city.region.name', read_only=True)
    plan_name = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    effective_end_date = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            'id', 'club', 'club_name', 'city_name', 'region_name', 
            'full_name', 'mobile', 'email', 'joined_at', 'is_active', 
            'created_at', 'subscription_plan', 'plan_name', 
            'start_date', 'end_date', 'effective_end_date'
        ]

    def get_plan_name(self, obj):
        sub = obj.subscriptions.filter(status='active').first()
        return sub.subscription_plan.name if sub else None

    def get_start_date(self, obj):
        sub = obj.subscriptions.filter(status='active').first()
        return sub.start_date.strftime('%Y-%m-%d') if sub else None

    def get_end_date(self, obj):
        sub = obj.subscriptions.filter(status='active').first()
        return sub.original_end_date.strftime('%Y-%m-%d') if sub else None

    def get_effective_end_date(self, obj):
        sub = obj.subscriptions.filter(status='active').first()
        return sub.effective_end_date.strftime('%Y-%m-%d') if sub else None

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
