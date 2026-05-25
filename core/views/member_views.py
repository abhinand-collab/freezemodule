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
    ).select_related('freeze', 'member_subscription__subscription_plan').order_by('-start_date')
    
    data = []
    for period in freeze_periods:
        data.append({
            'plan': period.member_subscription.subscription_plan.name,
            'start_date': period.start_date.strftime('%Y-%m-%d'),
            'end_date': period.end_date.strftime('%Y-%m-%d'),
            'reason': period.freeze.reason,
            'created_at': period.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return JsonResponse({'member_name': member.full_name, 'freezes': data})
