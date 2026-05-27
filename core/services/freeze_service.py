from datetime import timedelta

from core.models.freeze_models import FreezeLog, SubscriptionFreezePeriod
from core.models.subscription_models import MemberSubscription
from django.db import transaction

def merge_ranges(ranges):

    if not ranges:
        return []

    ranges.sort(key=lambda x: x[0])

    merged = [ranges[0]]

    for current_start, current_end in ranges[1:]:

        last_start, last_end = merged[-1]

        if current_start <= last_end + timedelta(days=1):

            merged[-1] = (
                last_start,
                max(last_end, current_end)
            )

        else:
            merged.append(
                (current_start, current_end)
            )

    return merged

def calculate_unique_freeze_days(subscription):

    periods = subscription.freeze_periods.all()

    ranges = [
        (p.start_date, p.end_date)
        for p in periods
    ]

    merged = merge_ranges(ranges)

    total_days = 0

    for start, end in merged:

        total_days += (end - start).days + 1

    return total_days



def apply_freeze_to_subscription(
    freeze,
    subscription
):

    with transaction.atomic():

        subscription = (
            MemberSubscription.objects
            .select_for_update()
            .get(id=subscription.id)
        )

        exists = (
            SubscriptionFreezePeriod.objects
            .filter(
                freeze=freeze,
                member_subscription=subscription
            )
            .exists()
        )

        if exists:
            return

        old_end_date = (
            subscription.effective_end_date
            or subscription.original_end_date
        )

        # Calculate proposed cumulative unique freeze days
        existing_periods = subscription.freeze_periods.all()
        ranges = [
            (p.start_date, p.end_date)
            for p in existing_periods
        ]
        ranges.append((freeze.start_date, freeze.end_date))
        
        merged_ranges = merge_ranges(ranges)
        proposed_total_days = 0
        for s_d, e_d in merged_ranges:
            proposed_total_days += (e_d - s_d).days + 1
            
        max_allowed = subscription.subscription_plan.max_freeze_days
        freeze_duration = (freeze.end_date - freeze.start_date).days + 1
        
        if proposed_total_days > max_allowed:
            current_total_days = calculate_unique_freeze_days(subscription)
            from django.utils import timezone
            FreezeLog.objects.create(
                freeze=freeze,
                member_subscription=subscription,
                old_end_date=old_end_date,
                new_end_date=None,
                freeze_days=freeze_duration,
                status="skipped",
                error_message=f"Proposed freeze ({freeze_duration} days) would increase total freeze days to {proposed_total_days} days, which exceeds the maximum allowed limit of {max_allowed} days (already frozen: {current_total_days} days).",
                processed_at=timezone.now()
            )
            return

        SubscriptionFreezePeriod.objects.create(
            freeze=freeze,
            member_subscription=subscription,
            start_date=freeze.start_date,
            end_date=freeze.end_date
        )

        unique_days = (
            calculate_unique_freeze_days(
                subscription
            )
        )

        subscription.effective_end_date = (
            subscription.original_end_date
            + timedelta(days=unique_days)
        )

        subscription.save()

        FreezeLog.objects.create(
            freeze=freeze,
            member_subscription=subscription,
            old_end_date=old_end_date,
            new_end_date=subscription.effective_end_date,
            freeze_days=unique_days,
            status="success"
        )

def get_target_subscriptions(freeze):
    if freeze.target_type == 'region':
        return MemberSubscription.objects.filter(member__club__city__region=freeze.region, status="active")
    elif freeze.target_type == 'city':
        return MemberSubscription.objects.filter(member__club__city=freeze.city, status="active")
    elif freeze.target_type == 'club':
        return MemberSubscription.objects.filter(member__club=freeze.club, status="active")
    elif freeze.target_type == 'member':
        return MemberSubscription.objects.filter(member=freeze.member, status="active")
    return MemberSubscription.objects.none()
