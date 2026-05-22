from django.shortcuts import render, redirect, get_object_or_404
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

def subscription_delete_view(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    plan.delete()
    return redirect('subscription_list')
