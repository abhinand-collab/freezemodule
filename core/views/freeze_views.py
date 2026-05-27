from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
import zoneinfo
from core.models.freeze_models import Freeze
from core.forms.freeze_forms import FreezeForm
from core.serializers.freeze_serializers import FreezeSerializer
from core.tasks import process_bulk_freeze

def generic_freeze_list_view(request, target_type):
    if request.method == 'POST':
        serializer = FreezeSerializer(data=request.POST)
        if serializer.is_valid():
            freeze = serializer.save()
            
            # Trigger Celery Task asynchronously
            process_bulk_freeze.delay(freeze.id)
            
            return redirect(f'{target_type}_freeze_list')
        
        form = FreezeForm(request.POST, target_type=target_type)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = FreezeForm(target_type=target_type)
        
    freezes = Freeze.objects.filter(target_type=target_type)
    if target_type == 'member':
        freezes = freezes.select_related('member__club__city__region')
    elif target_type == 'club':
        freezes = freezes.select_related('club__city__region')
    elif target_type == 'city':
        freezes = freezes.select_related('city__region')
    elif target_type == 'region':
        freezes = freezes.select_related('region')
    
    template_map = {
        'region': 'freezes/region_freeze_list.html',
        'city': 'freezes/city_freeze_list.html',
        'club': 'freezes/club_freeze_list.html',
        'member': 'freezes/member_freeze_list.html',
    }
    
    return render(request, template_map[target_type], {
        'freezes': freezes,
        'form': form,
        'target_type': target_type
    })

def region_freeze_list_view(request):
    return generic_freeze_list_view(request, 'region')

def city_freeze_list_view(request):
    return generic_freeze_list_view(request, 'city')

def club_freeze_list_view(request):
    return generic_freeze_list_view(request, 'club')

def member_freeze_list_view(request):
    return generic_freeze_list_view(request, 'member')

def get_freeze_status(request, freeze_id):
    freeze = get_object_or_404(Freeze, id=freeze_id)
    return JsonResponse({
        'id': freeze.id,
        'status': freeze.status,
        'processed_members': freeze.processed_members,
        'total_members': freeze.total_members,
        'error_logs': freeze.error_logs,
    })

def restart_freeze_view(request, freeze_id):
    freeze = get_object_or_404(Freeze, id=freeze_id)
    if freeze.status in ['failed', 'partial_failed']:
        freeze.status = 'pending'
        freeze.save()
        process_bulk_freeze.delay(freeze.id)
    
    target_type_map = {
        'region': 'region_freeze_list',
        'city': 'city_freeze_list',
        'club': 'club_freeze_list',
        'member': 'member_freeze_list',
    }
    return redirect(target_type_map.get(freeze.target_type, 'home'))

from django.db.models import Q

def get_target_freezes_view(request):
    target_type = request.GET.get('target_type')
    target_id = request.GET.get('target_id')

    if not (target_type and target_id):
        return JsonResponse({'freezes': [], 'max_date': None})

    from core.models.subscription_models import MemberSubscription
    from django.db.models import Max
    
    # Filter active subscriptions based on target to find the max allowed date
    subs_query = MemberSubscription.objects.filter(status='active')
    
    if target_type == 'region':
        subs_query = subs_query.filter(member__club__city__region_id=target_id)
    elif target_type == 'city':
        subs_query = subs_query.filter(member__club__city_id=target_id)
    elif target_type == 'club':
        subs_query = subs_query.filter(member__club_id=target_id)
    elif target_type == 'member':
        subs_query = subs_query.filter(member_id=target_id)
        
    max_date = subs_query.aggregate(Max('effective_end_date'))['effective_end_date__max']
    max_date_str = max_date.strftime('%Y-%m-%d') if max_date else None

    freezes = Freeze.objects.filter(
        target_type=target_type,
        is_active=True,
        status__in=['pending', 'processing', 'completed', 'partial_failed']
    )

    if target_type == 'region':
        freezes = freezes.filter(region_id=target_id)
    elif target_type == 'city':
        freezes = freezes.filter(city_id=target_id)
    elif target_type == 'club':
        freezes = freezes.filter(club_id=target_id)
    elif target_type == 'member':
        freezes = freezes.filter(member_id=target_id)

    data = [
        {'start_date': f.start_date.strftime('%Y-%m-%d'), 'end_date': f.end_date.strftime('%Y-%m-%d')}
        for f in freezes
    ]
    return JsonResponse({'freezes': data, 'max_date': max_date_str})


def get_freeze_details_view(request, freeze_id):
    freeze = get_object_or_404(Freeze, id=freeze_id)
    logs = freeze.logs.select_related('member_subscription__member', 'member_subscription__subscription_plan').all()
    
    log_list = []
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    for log in logs:
        processed_at_val = log.processed_at if log.processed_at else log.created_at
        if processed_at_val:
            processed_at_str = timezone.localtime(processed_at_val, ist_tz).strftime('%Y-%m-%d %H:%M:%S')
        else:
            processed_at_str = None

        log_list.append({
            'id': log.id,
            'member_name': log.member_subscription.member.full_name,
            'mobile': log.member_subscription.member.mobile,
            'plan_name': log.member_subscription.subscription_plan.name,
            'old_end_date': log.old_end_date.strftime('%Y-%m-%d') if log.old_end_date else None,
            'new_end_date': log.new_end_date.strftime('%Y-%m-%d') if log.new_end_date else None,
            'freeze_days': log.freeze_days,
            'status': log.status,
            'error_message': log.error_message,
            'processed_at': processed_at_str
        })
        
    # Append pending/unprocessed subscriptions
    from core.services.freeze_service import get_target_subscriptions
    target_subs = get_target_subscriptions(freeze)
    processed_sub_ids = freeze.logs.values_list('member_subscription_id', flat=True)
    pending_subs = target_subs.exclude(id__in=processed_sub_ids).select_related('member', 'subscription_plan')
    
    for sub in pending_subs:
        log_list.append({
            'member_name': sub.member.full_name,
            'mobile': sub.member.mobile,
            'plan_name': sub.subscription_plan.name,
            'old_end_date': (sub.effective_end_date or sub.original_end_date).strftime('%Y-%m-%d'),
            'new_end_date': None,
            'freeze_days': (freeze.end_date - freeze.start_date).days + 1,
            'status': 'pending',
            'error_message': '',
            'processed_at': None
        })

        
    return JsonResponse({
        'id': freeze.id,
        'target_type': freeze.target_type,
        'target_name': (
            freeze.region.name if freeze.target_type == 'region' and freeze.region else
            freeze.city.name if freeze.target_type == 'city' and freeze.city else
            freeze.club.name if freeze.target_type == 'club' and freeze.club else
            freeze.member.full_name if freeze.target_type == 'member' and freeze.member else 'Unknown'
        ),
        'status': freeze.status,
        'total_members': freeze.total_members,
        'processed_members': freeze.processed_members,
        'start_date': freeze.start_date.strftime('%Y-%m-%d'),
        'end_date': freeze.end_date.strftime('%Y-%m-%d'),
        'reason': freeze.reason,
        'error_logs': freeze.error_logs,
        'logs': log_list
    })


