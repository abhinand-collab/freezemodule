from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from core.models import SubscriptionPlan
from core.forms.subscription_forms import SubscriptionPlanForm
from core.serializers.subscription_serializers import SubscriptionPlanSerializer

def subscription_list_view(request):
    if request.method == 'POST':
        serializer = SubscriptionPlanSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return redirect('subscription_list')
        
        form = SubscriptionPlanForm(request.POST)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = SubscriptionPlanForm()
        
    query = request.GET.get('q')
    subscription_plans_queryset = SubscriptionPlan.objects.all().order_by('name')
    if query:
        subscription_plans_queryset = subscription_plans_queryset.filter(name__icontains=query)

    paginator = Paginator(subscription_plans_queryset, 10)  # Show 10 plans per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    
    return render(request, 'subscriptions/subscription_list.html', {
        'subscription_plans': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'form': form
    })
