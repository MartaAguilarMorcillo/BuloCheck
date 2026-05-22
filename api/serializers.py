from rest_framework import serializers

from .models import NewsCheck


class PredictRequestSerializer(serializers.Serializer):
    """Validates the input data for /api/predict/"""

    title = serializers.CharField(max_length=1000, allow_blank=True)
    text = serializers.CharField(allow_blank=True)
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
