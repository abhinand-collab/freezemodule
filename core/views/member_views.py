from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
import zoneinfo
from core.models import Member, MemberSubscription, FreezeLog
from core.models.freeze_models import SubscriptionFreezePeriod
from core.services.freeze_service import apply_freeze_to_subscription

def retry_member_freeze_view(request, log_id):
    log = get_object_or_404(FreezeLog, id=log_id)
    freeze = log.freeze
    subscription = log.member_subscription
    
    # Delete old log before retrying
    log.delete()
    
    try:
        apply_freeze_to_subscription(freeze, subscription)
        
        # After retry, check if main freeze status needs updating
        all_logs = freeze.logs.all()
        failed_count = all_logs.filter(status__in=['failed']).count()
        success_count = all_logs.filter(status='success').count()
        skipped_count = all_logs.filter(status='skipped').count()
        pending_count = all_logs.filter(status='pending').count()
        
        if failed_count == 0 and pending_count == 0:
            freeze.status = 'completed'
        elif success_count > 0 or skipped_count > 0:
            freeze.status = 'partial_failed'
        else:
            freeze.status = 'failed'
        freeze.save()
        
        # Get the new log
        new_log = freeze.logs.filter(member_subscription=subscription).latest('created_at')
        
        ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        processed_at_val = new_log.processed_at if new_log.processed_at else new_log.created_at
        
        return JsonResponse({
            'status': 'success',
            'message': 'Retry processed successfully.',
            'new_log': {
                'id': new_log.id,
                'status': new_log.status,
                'old_end_date': new_log.old_end_date.strftime('%Y-%m-%d') if new_log.old_end_date else None,
                'new_end_date': new_log.new_end_date.strftime('%Y-%m-%d') if new_log.new_end_date else None,
                'error_message': new_log.error_message,
                'processed_at': timezone.localtime(processed_at_val, ist_tz).strftime('%Y-%m-%d %H:%M:%S')
            },
            'summary': {
                'success': success_count,
                'failed': failed_count,
                'skipped': skipped_count,
                'pending': pending_count,
                'total': all_logs.count(),
                'freeze_status': freeze.status
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
from core.forms.member_forms import MemberForm
from core.serializers.member_serializers import MemberSerializer

def member_list_view(request):
    if request.method == 'POST' and request.headers.get('x-action') == 'fetch':
        query = request.POST.get('q')
        page_number = request.POST.get('page', 1)
        
        active_subscriptions = MemberSubscription.objects.all().select_related('subscription_plan')
        members_queryset = Member.objects.select_related('club__city__region').prefetch_related(
            Prefetch('subscriptions', queryset=active_subscriptions, to_attr='active_sub')
        ).order_by('-id')
        
        if query:
            members_queryset = members_queryset.filter(
                Q(full_name__icontains=query) |
                Q(mobile__icontains=query) |
                Q(email__icontains=query)
            )
            
        paginator = Paginator(members_queryset, 20)
        page_obj = paginator.get_page(page_number)
        page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))
        
        serializer = MemberSerializer(page_obj.object_list, many=True)
        
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
        serializer = MemberSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Member added successfully.'})
            return redirect('member_list')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': serializer.errors}, status=400)
            
        form = MemberForm(request.POST)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = MemberForm()
        
    query = request.GET.get('q')
    active_subscriptions = MemberSubscription.objects.all().select_related('subscription_plan')
    members_queryset = Member.objects.select_related('club__city__region').prefetch_related(
        Prefetch('subscriptions', queryset=active_subscriptions, to_attr='active_sub')
    ).order_by('-id')
    
    if query:
        members_queryset = members_queryset.filter(
            Q(full_name__icontains=query) |
            Q(mobile__icontains=query) |
            Q(email__icontains=query)
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        serializer = MemberSerializer(members_queryset, many=True)
        return JsonResponse({'status': 'success', 'data': serializer.data})

    paginator = Paginator(members_queryset, 20)  # Show 20 members per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    
    return render(request, 'members/member_list.html', {
        'members': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'form': form
    })

def member_delete_view(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    member.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Member deleted successfully.'})
    return redirect('member_list')

def member_freeze_history_view(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    freeze_periods = SubscriptionFreezePeriod.objects.filter(
        member_subscription__member=member
    ).select_related(
        'freeze__region', 'freeze__city', 'freeze__club', 'freeze__member',
        'member_subscription__subscription_plan'
    ).order_by('-created_at')
    
    from core.models.freeze_models import FreezeLog
    logs = FreezeLog.objects.filter(
        member_subscription__member=member,
        status="success"
    ).values('freeze_id', 'member_subscription_id', 'new_end_date')
    
    new_end_date_map = {
        (log['freeze_id'], log['member_subscription_id']): log['new_end_date']
        for log in logs
    }
    
    data = []
    for period in freeze_periods:
        duration = (period.end_date - period.start_date).days + 1
        
        target_type = period.freeze.target_type
        target_name = "-"
        if target_type == 'region' and period.freeze.region:
            target_name = period.freeze.region.name
        elif target_type == 'city' and period.freeze.city:
            target_name = period.freeze.city.name
        elif target_type == 'club' and period.freeze.club:
            target_name = period.freeze.club.name
        elif target_type == 'member' and period.freeze.member:
            target_name = "Individual"
            
        created_by_user = period.freeze.created_by if period.freeze.created_by else "System"
        
        new_end_date = new_end_date_map.get((period.freeze_id, period.member_subscription_id))
        new_end_date_str = new_end_date.strftime('%Y-%m-%d') if new_end_date else "-"

        ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        data.append({
            'plan': period.member_subscription.subscription_plan.name,
            'start_date': period.start_date.strftime('%Y-%m-%d'),
            'end_date': period.end_date.strftime('%Y-%m-%d'),
            'new_end_date': new_end_date_str,
            'duration_days': duration,
            'freeze_type': target_type.capitalize(),
            'target_name': target_name,
            'created_by': created_by_user,
            'reason': period.freeze.reason,
            'created_at': timezone.localtime(period.created_at, ist_tz).strftime('%Y-%m-%d %H:%M')
        })
    
    return JsonResponse({'member_name': member.full_name, 'freezes': data})
