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