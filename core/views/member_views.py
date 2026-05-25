from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from core.models import Member, MemberSubscription
from core.models.freeze_models import SubscriptionFreezePeriod
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
        
    active_subscriptions = MemberSubscription.objects.all().select_related('subscription_plan')
    members_queryset = Member.objects.select_related('club__city__region').prefetch_related(
        Prefetch('subscriptions', queryset=active_subscriptions, to_attr='active_sub')
    ).order_by('-id')
    
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

        data.append({
            'plan': period.member_subscription.subscription_plan.name,
            'start_date': period.start_date.strftime('%Y-%m-%d'),
            'end_date': period.end_date.strftime('%Y-%m-%d'),
            'duration_days': duration,
            'freeze_type': target_type.capitalize(),
            'target_name': target_name,
            'created_by': created_by_user,
            'reason': period.freeze.reason,
            'created_at': period.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return JsonResponse({'member_name': member.full_name, 'freezes': data})
