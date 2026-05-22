from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from core.models import Club
from core.forms.location_forms import ClubForm
from core.serializers.location_serializers import ClubSerializer

def club_list_view(request):
    if request.method == 'POST':
        serializer = ClubSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return redirect('club_list')
        
        form = ClubForm(request.POST)
        for field, errors in serializer.errors.items():
            for error in errors:
                form.add_error(field if field != 'non_field_errors' else None, error)
    else:
        form = ClubForm()
        
    clubs_queryset = Club.objects.select_related('city__region').all().order_by('name')
    paginator = Paginator(clubs_queryset, 10)  # Show 10 clubs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    
    return render(request, 'clubs/club_list.html', {
        'clubs': page_obj,
        'page_obj': page_obj,
        'page_range': page_range,
        'form': form
    })

def club_delete_view(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    club.delete()
    return redirect('club_list')
