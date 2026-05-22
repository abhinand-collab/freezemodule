from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from core.models import Region
from core.forms.location_forms import RegionForm
from core.serializers.location_serializers import RegionSerializer

def region_list_view(request):
    if request.method == 'POST':
        serializer = RegionSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return redirect('region_list')
        
        form = RegionForm(request.POST)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = RegionForm()
        
    regions_queryset = Region.objects.all().order_by('name')
    paginator = Paginator(regions_queryset, 10)  # Show 10 regions per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    
    return render(request, 'regions/region_list.html', {
        'regions': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'form': form
    })

def region_delete_view(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    region.delete()
    return redirect('region_list')
