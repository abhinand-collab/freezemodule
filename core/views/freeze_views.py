from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Max
import zoneinfo
from core.models.freeze_models import Freeze
from core.forms.freeze_forms import FreezeForm
from core.serializers.freeze_serializers import FreezeSerializer
from core.tasks import process_bulk_freeze

def generic_freeze_list_view(request, target_type):
    if request.method == 'POST' and request.headers.get('x-action') == 'fetch':
        query = request.POST.get('q')
        page_number = request.POST.get('page', 1)
        
        freezes = Freeze.objects.filter(target_type=target_type).order_by('-created_at')
        
        if query:
            q_objects = Q(reason__icontains=query) | Q(status__icontains=query)
            if target_type == 'member':
                q_objects |= Q(member__full_name__icontains=query)
            elif target_type == 'club':
                q_objects |= Q(club__name__icontains=query)
            elif target_type == 'city':
                q_objects |= Q(city__name__icontains=query)
            elif target_type == 'region':
                q_objects |= Q(region__name__icontains=query)
            freezes = freezes.filter(q_objects)
            
        if target_type == 'member':
            freezes = freezes.select_related('member__club__city__region')
        elif target_type == 'club':
            freezes = freezes.select_related('club__city__region')
        elif target_type == 'city':
            freezes = freezes.select_related('city__region')
        elif target_type == 'region':
            freezes = freezes.select_related('region')

        paginator = Paginator(freezes, 10)
        page_obj = paginator.get_page(page_number)
        page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))
        
        serializer = FreezeSerializer(page_obj.object_list, many=True)
        return JsonResponse({
            'status': 'success', 
            'data': serializer.data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'start_index': page_obj.start_index(),
                'end_index': page_obj.end_index(),
                'total_count': paginator.count,
                'page_range': page_range
            }
        })

    if request.method == 'POST':
        serializer = FreezeSerializer(data=request.POST)
        if serializer.is_valid():
            username = str(request.user) if request.user.is_authenticated else "System"
            freeze = serializer.save(created_by=username)
            
            # Trigger Celery Task asynchronously
            process_bulk_freeze.delay(freeze.id)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': f'{target_type.capitalize()} freeze initiated successfully.'})
            return redirect(f'{target_type}_freeze_list')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': serializer.errors}, status=400)
            
        form = FreezeForm(request.POST, target_type=target_type)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = FreezeForm(target_type=target_type)
        
    freezes_queryset = Freeze.objects.filter(target_type=target_type).order_by('-created_at')
    if target_type == 'member':
        freezes_queryset = freezes_queryset.select_related('member__club__city__region')
    elif target_type == 'club':
        freezes_queryset = freezes_queryset.select_related('club__city__region')
    elif target_type == 'city':
        freezes_queryset = freezes_queryset.select_related('city__region')
    elif target_type == 'region':
        freezes_queryset = freezes_queryset.select_related('region')
    
    paginator = Paginator(freezes_queryset, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    template_map = {
        'region': 'freezes/region_freeze_list.html',
        'city': 'freezes/city_freeze_list.html',
        'club': 'freezes/club_freeze_list.html',
        'member': 'freezes/member_freeze_list.html',
    }
    
    return render(request, template_map[target_type], {
        'freezes': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
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
        'target_name': freeze.target_name,
        'display_city': freeze.display_city,
        'display_club': freeze.display_club,
        'display_region': freeze.display_region,
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
    return JsonResponse({'freezes': data, 'max_date': None})


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
        'target_name': freeze.target_name,
        'status': freeze.status,
        'total_members': freeze.total_members,
        'processed_members': freeze.processed_members,
        'start_date': freeze.start_date.strftime('%Y-%m-%d'),
        'end_date': freeze.end_date.strftime('%Y-%m-%d'),
        'reason': freeze.reason,
        'error_logs': freeze.error_logs,
        'logs': log_list
    })


