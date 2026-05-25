from rest_framework import serializers
from core.models.freeze_models import Freeze, FreezeLog, SubscriptionFreezePeriod

class FreezeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Freeze
        exclude = ['is_active', 'task_id', 'total_members', 'processed_members', 'error_logs', 'created_by']

    def validate(self, attrs):
        target_type = attrs.get('target_type')
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("End date must be after or equal to start date.")

            # Get active subscriptions for target
            from core.models.subscription_models import MemberSubscription
            subs = MemberSubscription.objects.filter(status="active")
            
            if target_type == 'region':
                region = attrs.get('region')
                if not region:
                    raise serializers.ValidationError({"region": "Region is required for a region freeze."})
                subs = subs.filter(member__club__city__region=region)
            elif target_type == 'city':
                city = attrs.get('city')
                if not city:
                    raise serializers.ValidationError({"city": "City is required for a city freeze."})
                subs = subs.filter(member__club__city=city)
            elif target_type == 'club':
                club = attrs.get('club')
                if not club:
                    raise serializers.ValidationError({"club": "Club is required for a club freeze."})
                subs = subs.filter(member__club=club)
            elif target_type == 'member':
                member = attrs.get('member')
                if not member:
                    raise serializers.ValidationError({"member": "Member is required for a member freeze."})
                subs = subs.filter(member=member)
            else:
                raise serializers.ValidationError("Invalid target type.")

            # For bulk freezes, we only check if there are any active subscriptions at all
            if target_type != 'member':
                if not subs.exists():
                    raise serializers.ValidationError("No active subscriptions found for the selected target.")
            else:
                # Individual member strict validations
                freeze_duration = (end_date - start_date).days + 1
                
                # Check maximum freeze duration limit against subscription plan
                exceeded_plans = subs.filter(subscription_plan__max_freeze_days__lt=freeze_duration).select_related('subscription_plan', 'member')
                if exceeded_plans.exists():
                    first_exceeded = exceeded_plans.first()
                    plan_name = first_exceeded.subscription_plan.name
                    max_allowed = first_exceeded.subscription_plan.max_freeze_days
                    raise serializers.ValidationError(
                        f"The freeze duration ({freeze_duration} days) exceeds the maximum allowed limit of {max_allowed} days for subscription plan '{plan_name}'."
                    )

                # Validate start date is not after current end date
                from django.db.models import Q
                expired_subs = subs.filter(
                    Q(effective_end_date__isnull=False, effective_end_date__lt=start_date) |
                    Q(effective_end_date__isnull=True, original_end_date__lt=start_date)
                )
                if expired_subs.exists():
                    first_expired = expired_subs.first()
                    current_end = (first_expired.effective_end_date or first_expired.original_end_date).strftime('%Y-%m-%d')
                    raise serializers.ValidationError(
                        f"Freeze start date ({start_date}) cannot be after the subscription end date ({current_end})."
                    )

                # Check overlapping SubscriptionFreezePeriod
                from core.models.freeze_models import SubscriptionFreezePeriod
                overlapping = SubscriptionFreezePeriod.objects.filter(
                    member_subscription__in=subs,
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
                if overlapping.exists():
                    first_overlap = overlapping.first()
                    overlap_start = first_overlap.start_date.strftime('%Y-%m-%d')
                    overlap_end = first_overlap.end_date.strftime('%Y-%m-%d')
                    raise serializers.ValidationError(
                        f"Selected dates overlap with an existing freeze ({overlap_start} to {overlap_end})."
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
