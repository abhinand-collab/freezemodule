from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
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

