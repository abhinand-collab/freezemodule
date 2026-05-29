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

        old_end_date = (
            subscription.effective_end_date
            or subscription.original_end_date
        )
        subscription_start = subscription.start_date

        # 1. Determine the actual overlap between freeze period and CURRENT subscription period
        applied_start_date = max(freeze.start_date, subscription_start)
        applied_end_date = min(freeze.end_date, old_end_date)
        
        if applied_start_date > applied_end_date:
            # Only log "Skipped" if this is the first time we're seeing this freeze and it doesn't overlap at all
            if not SubscriptionFreezePeriod.objects.filter(freeze=freeze, member_subscription=subscription).exists():
                from django.utils import timezone
                FreezeLog.objects.create(
                    freeze=freeze,
                    member_subscription=subscription,
                    old_end_date=old_end_date,
                    new_end_date=None,
                    freeze_days=(freeze.end_date - freeze.start_date).days + 1,
                    status="skipped",
                    error_message=f"No overlap between freeze ({freeze.start_date} to {freeze.end_date}) and membership ({subscription_start} to {old_end_date}).",
                    processed_at=timezone.now()
                )
            return

        # 2. Check if we already have a record for this freeze
        period = SubscriptionFreezePeriod.objects.filter(
            freeze=freeze,
            member_subscription=subscription
        ).first()

        if period and period.start_date == applied_start_date and period.end_date == applied_end_date:
            # Already up to date
            return

        # 3. Calculate proposed cumulative unique freeze days if we apply/update this
        existing_ranges = [
            (p.start_date, p.end_date)
            for p in subscription.freeze_periods.all()
            if p.id != (period.id if period else None)
        ]
        existing_ranges.append((applied_start_date, applied_end_date))
        
        merged_ranges = merge_ranges(existing_ranges)
        proposed_total_days = 0
        for s_d, e_d in merged_ranges:
            proposed_total_days += (e_d - s_d).days + 1
            
        max_allowed = subscription.subscription_plan.max_freeze_days
        
        if proposed_total_days > max_allowed:
            # If we exceed, we skip or clip to the limit
            if not period:
                from django.utils import timezone
                current_total_days = calculate_unique_freeze_days(subscription)
                FreezeLog.objects.create(
                    freeze=freeze,
                    member_subscription=subscription,
                    old_end_date=old_end_date,
                    new_end_date=None,
                    freeze_days=(applied_end_date - applied_start_date).days + 1,
                    status="skipped",
                    error_message=f"Freeze exceeds plan limit of {max_allowed} days.",
                    processed_at=timezone.now()
                )
            return

        # 4. Save or Update the record
        from django.utils import timezone
        is_update = period is not None
        if not period:
            SubscriptionFreezePeriod.objects.create(
                freeze=freeze,
                member_subscription=subscription,
                start_date=applied_start_date,
                end_date=applied_end_date
            )
        else:
            period.start_date = applied_start_date
            period.end_date = applied_end_date
            period.save()

        # 5. Recalculate unique days and shift the effective end date
        unique_days = calculate_unique_freeze_days(subscription)
        subscription.effective_end_date = subscription.original_end_date + timedelta(days=unique_days)
        subscription.save()

        # 6. Update Freeze counters (Only for brand new applications, not shifts)
        if not is_update:
            from django.db.models import F
            freeze.total_members = F('total_members') + 1
            freeze.processed_members = F('processed_members') + 1
            freeze.save(update_fields=['total_members', 'processed_members'])

            FreezeLog.objects.create(
                freeze=freeze,
                member_subscription=subscription,
                old_end_date=old_end_date,
                new_end_date=subscription.effective_end_date,
                freeze_days=unique_days,
                status="success",
                error_message=f"Applied and shifted end date to {subscription.effective_end_date}.",
                processed_at=timezone.now()
            )

        # 7. IMPORTANT: Chain Reaction
        # Now that the end date has potentially moved, we might overlap with OTHER 
        # location freezes that we previously skipped or clipped.
        apply_existing_freezes_to_subscription(subscription)

def apply_existing_freezes_to_subscription(subscription):
    """
    Finds and applies any existing location-based freezes that overlap with this subscription.
    This is called iteratively to handle shifting end dates.
    """
    from core.models.freeze_models import Freeze
    from django.db.models import Q
    
    member = subscription.member
    club = member.club
    city = club.city
    region = city.region
    
    # We loop until no more freezes can be applied or expanded
    changed = True
    while changed:
        changed = False
        old_end = subscription.effective_end_date
        
        relevant_freezes = Freeze.objects.filter(
            Q(target_type='region', region=region) |
            Q(target_type='city', city=city) |
            Q(target_type='club', club=club) |
            Q(target_type='member', member=member),
            status__in=['pending', 'processing', 'completed', 'partial_failed'],
            is_active=True
        ).order_by('start_date')
        
        for freeze in relevant_freezes:
            apply_freeze_to_subscription(freeze, subscription)
            # Refetch to see if end date moved
            subscription.refresh_from_db()
            if subscription.effective_end_date != old_end:
                changed = True
                break # Start over with the new end date


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
