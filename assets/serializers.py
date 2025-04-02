from rest_framework import serializers
from .models import asset, lease, documentz, similarityz

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = asset
        fields = '__all__'

class LeaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = lease
        fields = '__all__'
