from django.http import JsonResponse
from django.db.models import Q, Prefetch
from core.models import City, Club, Member, MemberSubscription

def get_cities_ajax(request):
    region_id = request.GET.get('region_id')
    cities = City.objects.filter(region_id=region_id).order_by('name')
    return JsonResponse([{'id': c.id, 'name': c.name} for c in cities], safe=False)

def get_clubs_ajax(request):
    city_id = request.GET.get('city_id')
    clubs = Club.objects.filter(city_id=city_id).order_by('name')
    return JsonResponse([{'id': c.id, 'name': c.name} for c in clubs], safe=False)

def get_members_ajax(request):
    club_id = request.GET.get('club_id')
    query = request.GET.get('q')
    
    members = Member.objects.filter(club_id=club_id)
    
    if query:
        members = members.filter(
            Q(full_name__icontains=query) | Q(mobile__icontains=query)
        )
    
    active_subs = MemberSubscription.objects.filter(status='active').order_by('-effective_end_date')
    
    members = members.prefetch_related(
        Prefetch('subscriptions', queryset=active_subs, to_attr='latest_active_sub')
    ).order_by('full_name')[:50] # Limit to 50 for performance
    
    data = []
    for m in members:
        latest_sub = m.latest_active_sub[0] if m.latest_active_sub else None
        data.append({
            'id': m.id, 
            'name': f"{m.full_name} ({m.mobile})",
            'max_date': latest_sub.effective_end_date.strftime('%Y-%m-%d') if latest_sub and latest_sub.effective_end_date else None
        })
    return JsonResponse(data, safe=False)
