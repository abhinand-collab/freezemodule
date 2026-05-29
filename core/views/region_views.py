from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from core.models import Region
from core.forms.location_forms import RegionForm
from core.serializers.location_serializers import RegionSerializer

def region_list_view(request):
    if request.method == 'POST' and request.headers.get('x-action') == 'fetch':
        query = request.POST.get('q')
        page_number = request.POST.get('page', 1)
        
        regions_queryset = Region.objects.all().order_by('name')
        if query:
            regions_queryset = regions_queryset.filter(name__icontains=query)
            
        paginator = Paginator(regions_queryset, 10)
        page_obj = paginator.get_page(page_number)
        page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))
        
        serializer = RegionSerializer(page_obj.object_list, many=True)
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
        serializer = RegionSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Region added successfully.'})
            return redirect('region_list')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': serializer.errors}, status=400)
            
        form = RegionForm(request.POST)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = RegionForm()
        
    query = request.GET.get('q')
    regions_queryset = Region.objects.all().order_by('name')
    if query:
        regions_queryset = regions_queryset.filter(name__icontains=query)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        serializer = RegionSerializer(regions_queryset, many=True)
        return JsonResponse({'status': 'success', 'data': serializer.data})

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
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Region deleted successfully.'})
    return redirect('region_list')
