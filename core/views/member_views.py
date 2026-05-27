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
    
    # Delete old log before retrying to maintain single entry per freeze/sub if desired, 
    # but apply_freeze_to_subscription creates a new one. 
    # Let's delete the failed/skipped one first.
    log.delete()
    
    try:
        apply_freeze_to_subscription(freeze, subscription)
        
        # After retry, check if main freeze status needs updating
        all_logs = freeze.logs.all()
        failed_count = all_logs.filter(status__in=['failed']).count()
        success_count = all_logs.filter(status='success').count()
        
        if failed_count == 0:
            freeze.status = 'completed'
        elif success_count > 0:
            freeze.status = 'partial_failed'
        else:
            freeze.status = 'failed'
        freeze.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
from core.forms.member_forms import MemberForm
from core.serializers.member_serializers import MemberSerializer

def member_list_view(request):
    if request.method == 'POST':
        serializer = MemberSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return redirect('member_list')
        
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
    return redirect('member_list')

def member_freeze_history_view(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    freeze_periods = SubscriptionFreezePeriod.objects.filter(
        member_subscription__member=member
    ).select_related(
        'freeze__region', 'freeze__city', 'freeze__club', 'freeze__member', 'freeze__created_by',
        'member_subscription__subscription_plan'
    ).order_by('-start_date')
    
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
            
        created_by_user = period.freeze.created_by.username if period.freeze.created_by else "System"
        
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
