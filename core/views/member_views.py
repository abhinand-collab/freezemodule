from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch
from django.core.paginator import Paginator
from core.models import Member, MemberSubscription
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
