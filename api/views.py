from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ml import predict_news
from .models import AnonymousUser, NewsCheck
from .serializers import NewsCheckSerializer, PredictRequestSerializer


class PredictView(APIView):
    """
    POST /api/predict/

    Receives title, text, source (optional) and device_id.
    Calls the model on HuggingFace Space, saves the result in DB and returns it.

    Request body:
        {
            "title": "...",
            "text": "...",
            "source": "bbc.com",     <- optional
            "device_id": "uuid"
        }

    Response:
        {
            "label": "FAKE" | "REAL",
            "confidence": 0.94,
            "probas": {"REAL": 0.06, "FAKE": 0.94},
            "check_id": 1
        }
    """

    def post(self, request):
        # 1. Validate input
        serializer = PredictRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        device_id = data["device_id"]
        title = data["title"]
        text = data["text"]
        source = data.get("source") or None

        # 2. Get or create anonymous user by device_id
        user, _ = AnonymousUser.objects.get_or_create(id=device_id)

        # 3. Call the model
        try:
            result = predict_news(title=title, text=text)
        except Exception as e:
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                return Response(
                    {
                        "error": "The model is waking up, please try again in 30 seconds."
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response(
                {"error": error_msg},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 4. Save to database
        check = NewsCheck.objects.create(
            user=user,
            title=title,
            text=text,
            source=source,
            label=result["label"],
            confidence=result["confidence"],
        )

        # 5. Return result
        return Response(
            {
                "label": result["label"],
                "confidence": result["confidence"],
                "probas": result["probas"],
                "check_id": check.id,
            },
            status=status.HTTP_200_OK,
        )


class HistoryView(APIView):
    """
    GET /api/history/

    Returns the list of news articles analyzed by the user.
    Requires header: X-Device-ID

    Response:
        [
            {
                "id": 1,
                "title": "...",
                "text": "...",
                "source": "bbc.com",
                "label": "REAL",
                "confidence": 0.94,
                "created_at": "2026-05-16T20:49:36Z"
            },
            ...
        ]
    """

    def get(self, request):
        device_id = request.headers.get("X-Device-ID")
        if not device_id:
            return Response(
                {"error": "Missing X-Device-ID header"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = AnonymousUser.objects.get(id=device_id)
        except AnonymousUser.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        checks = user.checks.all()
        serializer = NewsCheckSerializer(checks, many=True)
        return Response(serializer.data)


class SourceStatsView(APIView):
    """
    GET /api/sources/

    Returns the top 5 most reliable news sources for the user,
    based on their search history.

    Ordering criteria:
        1. Primary:   number of articles labeled REAL (descending)
        2. Tiebreak:  average confidence of REAL articles (descending)

    Requires header: X-Device-ID

    Response:
        [
            {
                "source": "The New York Times",
                "total": 2,
                "real": 2,
                "fake": 0,
                "real_confidence_avg": 0.85,
                "reliability_pct": 100.0
            },
            ...
        ]

    Example (from the problem statement):
        - BBC:              2 REAL @ 80% avg  → 2nd
        - The New York Times: 2 REAL @ 85% avg → 1st (tiebreak: higher confidence)
        - BuzzFeed:         1 REAL @ 81% avg  → 3rd
        - Fox News:         0 REAL, 3 FAKE    → 4th
    """

    def get(self, request):
        device_id = request.headers.get("X-Device-ID")
        if not device_id:
            return Response(
                {"error": "Missing X-Device-ID header"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = AnonymousUser.objects.get(id=device_id)
        except AnonymousUser.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        # Only news checks with a source informed
        checks = user.checks.filter(source__isnull=False).exclude(source="")

        if not checks.exists():
            return Response([], status=status.HTTP_200_OK)

        # Group by source
        stats = {}
        for check in checks:
            src = check.source
            if src not in stats:
                stats[src] = {
                    "source": src,
                    "total": 0,
                    "real": 0,
                    "fake": 0,
                    "real_confidence_sum": 0.0,
                }
            stats[src]["total"] += 1
            if check.label == "REAL":
                stats[src]["real"] += 1
                stats[src]["real_confidence_sum"] += check.confidence
            else:
                stats[src]["fake"] += 1

        # Calculate reliability metrics
        result = []
        for src_data in stats.values():
            real_count = src_data["real"]
            total = src_data["total"]

            # Average confidence of REAL articles (used as tiebreaker)
            real_confidence_avg = (
                round(src_data["real_confidence_sum"] / real_count, 4)
                if real_count > 0
                else 0.0
            )

            result.append(
                {
                    "source": src_data["source"],
                    "total": total,
                    "real": real_count,
                    "fake": src_data["fake"],
                    "real_confidence_avg": real_confidence_avg,
                    "reliability_pct": round(real_count / total * 100, 1),
                }
            )

        # Sort: 1st by number of REAL articles (desc), 2nd by avg confidence (desc)
        result.sort(
            key=lambda x: (x["real"], x["real_confidence_avg"]),
            reverse=True,
        )

        # Return top 5
        return Response(result[:5])
