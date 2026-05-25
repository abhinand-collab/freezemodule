from django.shortcuts import render, redirect
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
        
    subscription_plans = SubscriptionPlan.objects.all()
    return render(request, 'subscriptions/subscription_list.html', {
        'subscription_plans': subscription_plans,
        'form': form
    })
