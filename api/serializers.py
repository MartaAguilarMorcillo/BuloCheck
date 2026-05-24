from rest_framework import serializers

from .models import NewsCheck, NewsSource


class PredictRequestSerializer(serializers.Serializer):
    """Validates the input data for POST /api/predict/"""

    title = serializers.CharField(max_length=1000, allow_blank=True)
    text = serializers.CharField(allow_blank=True)
    # domain extracted by the Chrome extension from the page URL
    domain = serializers.CharField(max_length=200, required=False, allow_blank=True)
    device_id = serializers.UUIDField()


class NewsSourceSerializer(serializers.ModelSerializer):
    """Serializes a NewsSource for embedding in responses."""

    class Meta:
        model = NewsSource
        fields = ["id", "name", "domain", "logo_url", "is_predefined"]


class NewsCheckSerializer(serializers.ModelSerializer):
    """Serializes a NewsCheck including the full NewsSource object."""

    news_source = NewsSourceSerializer(read_only=True)

    class Meta:
        model = NewsCheck
        fields = [
            "id",
            "title",
            "text",
            "news_source",
            "label",
            "confidence",
            "created_at",
        ]
