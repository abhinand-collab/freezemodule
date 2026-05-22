from rest_framework import serializers
from core.models.location_models import Region, City, Club

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'is_active', 'created_at']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'region', 'name', 'is_active', 'created_at']

class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ['id', 'city', 'name', 'address', 'is_active', 'created_at']
