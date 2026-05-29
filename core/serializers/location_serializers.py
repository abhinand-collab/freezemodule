from rest_framework import serializers
from core.models.location_models import Region, City, Club

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'is_active', 'created_at']

class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    class Meta:
        model = City
        fields = ['id', 'region', 'region_name', 'name', 'is_active', 'created_at']

class ClubSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    region_name = serializers.CharField(source='city.region.name', read_only=True)
    class Meta:
        model = Club
        fields = ['id', 'city', 'city_name', 'region_name', 'name', 'address', 'is_active', 'created_at']
