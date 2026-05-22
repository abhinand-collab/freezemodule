from django.urls import path
from core.views.home_views import home_view
from core.views.region_views import region_list_view, region_delete_view
from core.views.city_views import city_list_view, city_delete_view
from core.views.club_views import club_list_view, club_delete_view
from core.views.member_views import member_list_view, member_delete_view
from core.views.subscription_views import subscription_list_view, subscription_delete_view

from core.views.freeze_views import (
    region_freeze_list_view, city_freeze_list_view, 
    club_freeze_list_view, member_freeze_list_view,
    get_freeze_status
)

urlpatterns = [
    path('', home_view, name='home'),
    path('regions/', region_list_view, name='region_list'),
    path('regions/<int:region_id>/delete/', region_delete_view, name='region_delete'),
    path('cities/', city_list_view, name='city_list'),
    path('cities/<int:city_id>/delete/', city_delete_view, name='city_delete'),
    path('clubs/', club_list_view, name='club_list'),
    path('clubs/<int:club_id>/delete/', club_delete_view, name='club_delete'),
    path('members/', member_list_view, name='member_list'),
    path('members/<int:member_id>/delete/', member_delete_view, name='member_delete'),
    path('subscriptions/', subscription_list_view, name='subscription_list'),
    path('subscriptions/<int:plan_id>/delete/', subscription_delete_view, name='subscription_delete'),
    
    # Freeze URLs
    path('freezes/region/', region_freeze_list_view, name='region_freeze_list'),
    path('freezes/city/', city_freeze_list_view, name='city_freeze_list'),
    path('freezes/club/', club_freeze_list_view, name='club_freeze_list'),
    path('freezes/member/', member_freeze_list_view, name='member_freeze_list'),
    path('freezes/<int:freeze_id>/status/', get_freeze_status, name='get_freeze_status'),
]
