from rest_framework import serializers

from .models import NewsCheck


class PredictRequestSerializer(serializers.Serializer):
    """Valida los datos de entrada del endpoint /api/predict/"""

    title = serializers.CharField(max_length=1000)
    text = serializers.CharField()
    source = serializers.CharField(max_length=500, required=False, allow_blank=True)
    device_id = serializers.UUIDField()


class NewsCheckSerializer(serializers.ModelSerializer):
    """Serializa un registro de NewsCheck para devolverlo al cliente."""

    class Meta:
        model = NewsCheck
        fields = [
            "id",
            "title",
            "text",
            "source",
            "label",
            "confidence",
            "created_at",
        ]
