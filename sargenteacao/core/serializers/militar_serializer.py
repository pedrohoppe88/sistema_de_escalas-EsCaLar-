from rest_framework import serializers
from ..models import Militar

class MilitarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Militar
        fields = '__all__'
