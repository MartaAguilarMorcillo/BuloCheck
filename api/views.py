from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .ml import predict_news
from .models import NewsCheck, NewsSource
from .serializers import (
    NewsCheckSerializer, NewsSourceSerializer,
    PredictRequestSerializer, RegisterSerializer,
)
from .source_utils import get_or_create_source
from .validators import validate_body, validate_title

User = get_user_model()


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new user and returns JWT tokens.
    Request: { "email": "...", "password": "..." }
    Response: { "access": "...", "refresh": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_201_CREATED)


class PredictView(APIView):
    """POST /api/predict/ — requires authentication."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PredictRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        title = data["title"]
        text = data["text"]
        domain = data.get("domain", "").strip() or None

        # Validate content
        title_validation = validate_title(title)
        body_validation = validate_body(text)
        errors = title_validation.errors + body_validation.errors
        if errors:
            return Response(
                {"validation_errors": errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        warnings = title_validation.warnings + body_validation.warnings

        # Resolve news source
        news_source = get_or_create_source(domain) if domain else None

        # Check if article already exists
        user = request.user
        existing_check = NewsCheck.objects.filter(
            title=title, text=text, news_source=news_source,
        ).first()

        if existing_check:
            existing_check.users.add(user)
            response_data = {
                "label": existing_check.label,
                "confidence": existing_check.confidence,
                "probas": {
                    "REAL": round(existing_check.confidence if existing_check.label == "REAL"
                                  else 1 - existing_check.confidence, 4),
                    "FAKE": round(existing_check.confidence if existing_check.label == "FAKE"
                                  else 1 - existing_check.confidence, 4),
                },
                "check_id": existing_check.id,
                "news_source": NewsSourceSerializer(news_source).data if news_source else None,
                "from_cache": True,
            }
            if warnings:
                response_data["warnings"] = warnings
            return Response(response_data, status=status.HTTP_200_OK)

        # Call the model
        try:
            result = predict_news(title=title, text=text)
        except Exception as e:
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                return Response(
                    {"error": "The model is waking up, please try again in 30 seconds."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response(
                {"error": error_msg},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        check = NewsCheck.objects.create(
            title=title, text=text, news_source=news_source,
            label=result["label"], confidence=result["confidence"],
        )
        check.users.add(user)

        response_data = {
            "label": result["label"],
            "confidence": result["confidence"],
            "probas": result["probas"],
            "check_id": check.id,
            "news_source": NewsSourceSerializer(news_source).data if news_source else None,
            "from_cache": False,
        }
        if warnings:
            response_data["warnings"] = warnings
        return Response(response_data, status=status.HTTP_200_OK)


class HistoryView(APIView):
    """GET /api/history/ — paginated history for the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        try:
            page_size = min(50, max(1, int(request.query_params.get("page_size", 10))))
        except ValueError:
            page_size = 10

        checks = request.user.checks.select_related("news_source").all()
        total = checks.count()
        total_pages = max(1, -(-total // page_size))
        page_checks = checks[(page - 1) * page_size: page * page_size]

        return Response({
            "count": total,
            "total_pages": total_pages,
            "current_page": page,
            "results": NewsCheckSerializer(page_checks, many=True).data,
        })


class SourceStatsView(APIView):
    """GET /api/sources/ — top 5 most reliable sources for the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        checks = request.user.checks.filter(
            news_source__isnull=False
        ).select_related("news_source")

        if not checks.exists():
            return Response([])

        stats = {}
        for check in checks:
            src_id = check.news_source.id
            if src_id not in stats:
                stats[src_id] = {
                    "news_source": check.news_source,
                    "total": 0, "real": 0, "fake": 0,
                    "real_confidence_sum": 0.0,
                }
            stats[src_id]["total"] += 1
            if check.label == "REAL":
                stats[src_id]["real"] += 1
                stats[src_id]["real_confidence_sum"] += check.confidence
            else:
                stats[src_id]["fake"] += 1

        result = []
        for src_data in stats.values():
            real_count = src_data["real"]
            real_confidence_avg = (
                round(src_data["real_confidence_sum"] / real_count, 4)
                if real_count > 0 else 0.0
            )
            result.append({
                "news_source": NewsSourceSerializer(src_data["news_source"]).data,
                "total": src_data["total"],
                "real": real_count,
                "fake": src_data["fake"],
                "real_confidence_avg": real_confidence_avg,
                "reliability_pct": round(real_count / src_data["total"] * 100, 1),
            })

        result.sort(key=lambda x: (x["real"], x["real_confidence_avg"]), reverse=True)
        return Response(result[:5])


class SourceLookupView(APIView):
    """GET /api/sources/lookup/?domain=bbc.com"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        domain = request.query_params.get("domain", "").strip().lower()
        if not domain:
            return Response(
                {"error": "Query parameter 'domain' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            source = NewsSource.objects.get(domain=domain)
            return Response(NewsSourceSerializer(source).data)
        except NewsSource.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class SimilarNewsView(APIView):
    """GET /api/similar/?title=... — hybrid trigram + full-text search."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        title = request.query_params.get("title", "").strip()
        if not title:
            return Response(
                {"error": "Query parameter 'title' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            min_sim = float(request.query_params.get("min_sim", 0.25))
        except ValueError:
            min_sim = 0.25

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT nc.title, ns.name, ns.logo_url, nc.label,
                    ROUND(COALESCE(similarity(nc.title, %s), 0)::numeric, 4),
                    ROUND(COALESCE(ts_rank(to_tsvector('english', nc.title),
                        plainto_tsquery('english', %s)), 0)::numeric, 4),
                    CASE
                        WHEN similarity(nc.title, %s) >= %s
                         AND to_tsvector('english', nc.title) @@ plainto_tsquery('english', %s)
                        THEN 'trigram+fulltext'
                        WHEN similarity(nc.title, %s) >= %s THEN 'trigram'
                        ELSE 'fulltext'
                    END
                FROM news_checks nc
                LEFT JOIN news_sources ns ON nc.news_source_id = ns.id
                WHERE nc.title != %s
                  AND (similarity(nc.title, %s) >= %s
                       OR ts_rank(to_tsvector('english', nc.title),
                          plainto_tsquery('english', %s)) >= %s)
                ORDER BY (COALESCE(similarity(nc.title, %s), 0) +
                    COALESCE(ts_rank(to_tsvector('english', nc.title),
                        plainto_tsquery('english', %s)), 0)) DESC
                LIMIT 5
            """, [
                title, title,
                title, min_sim, title,
                title, min_sim,
                title,
                title, min_sim, title, min_sim,
                title, title,
            ])
            rows = cursor.fetchall()

        return Response([{
            "title": r[0], "source_name": r[1], "source_logo": r[2],
            "label": r[3], "similarity": float(r[4]),
            "fts_rank": float(r[5]), "match_type": r[6],
        } for r in rows])