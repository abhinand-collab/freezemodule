from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from core.models import City
from core.forms.location_forms import CityForm
from core.serializers.location_serializers import CitySerializer

def city_list_view(request):
    if request.method == 'POST':
        serializer = CitySerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return redirect('city_list')
        
        form = CityForm(request.POST)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = CityForm()
        
    query = request.GET.get('q')
    cities_queryset = City.objects.select_related('region').all().order_by('name')
    if query:
        cities_queryset = cities_queryset.filter(name__icontains=query)

    paginator = Paginator(cities_queryset, 10)  # Show 10 cities per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    
    return render(request, 'cities/city_list.html', {
        'cities': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'form': form
    })

def city_delete_view(request, city_id):
    city = get_object_or_404(City, id=city_id)
    city.delete()
    return redirect('city_list')
