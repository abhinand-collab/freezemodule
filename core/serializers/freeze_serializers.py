from rest_framework import serializers
from django.utils import timezone
from core.models.freeze_models import Freeze, FreezeLog, SubscriptionFreezePeriod

class FreezeSerializer(serializers.ModelSerializer):
    target_name = serializers.SerializerMethodField()
    display_city = serializers.SerializerMethodField()
    display_club = serializers.SerializerMethodField()
    display_region = serializers.SerializerMethodField()

    class Meta:
        model = Freeze
        fields = [
            'id', 'target_type', 'status', 'start_date', 'end_date', 
            'reason', 'total_members', 'processed_members', 'created_at',
            'target_name', 'display_city', 'display_club', 'display_region',
            'region', 'city', 'club', 'member'
        ]

    def get_target_name(self, obj):
        return obj.target_name

    def get_display_region(self, obj):
        return obj.display_region

    def get_display_city(self, obj):
        return obj.display_city

    def get_display_club(self, obj):
        return obj.display_club

    def validate(self, attrs):
        target_type = attrs.get('target_type')
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("End date must be after or equal to start date.")
            
            if start_date < timezone.now().date():
                raise serializers.ValidationError("Start date cannot be in the past.")

            # Get active subscriptions for target
            from core.models.subscription_models import MemberSubscription
            subs = MemberSubscription.objects.filter(status="active")
            
            if target_type == 'region':
                region = attrs.get('region')
                if not region: raise serializers.ValidationError({"region": "Region is required."})
                subs = subs.filter(member__club__city__region=region)
            elif target_type == 'city':
                city = attrs.get('city')
                if not city: raise serializers.ValidationError({"city": "City is required."})
                subs = subs.filter(member__club__city=city)
            elif target_type == 'club':
                club = attrs.get('club')
                if not club: raise serializers.ValidationError({"club": "Club is required."})
                subs = subs.filter(member__club=club)
            elif target_type == 'member':
                member = attrs.get('member')
                if not member: raise serializers.ValidationError({"member": "Member is required."})
                subs = subs.filter(member=member)
            else:
                raise serializers.ValidationError("Invalid target type.")

            if not subs.exists():
                raise serializers.ValidationError("No active subscriptions found for the selected target.")

            # 1. Overlapping Check (Only for individual member freezes)
            if target_type == 'member':
                overlaps = SubscriptionFreezePeriod.objects.filter(
                    member_subscription__in=subs,
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                if overlaps.exists():
                    raise serializers.ValidationError("Selected dates overlap with an existing freeze for this member.")

            # 3. Cumulative Duration Check (Only for individual member freezes)
            if target_type == 'member':
                new_days = (end_date - start_date).days + 1
                for sub in subs.select_related('subscription_plan'):
                    from core.services.freeze_service import calculate_unique_freeze_days
                    current_days = calculate_unique_freeze_days(sub)
                    if current_days + new_days > sub.subscription_plan.max_freeze_days:
                        raise serializers.ValidationError(
                            f"Freeze duration ({new_days} days) exceeds the maximum allowed limit of {sub.subscription_plan.max_freeze_days} days "
                            f"for subscription plan '{sub.subscription_plan.name}' (already used: {current_days} days)."
                        )

        return attrs

class FreezeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreezeLog
        fields = '__all__'

class SubscriptionFreezePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFreezePeriod
        fields = '__all__'
