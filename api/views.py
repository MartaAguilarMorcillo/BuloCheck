from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ml import predict_news
from .models import AnonymousUser, NewsCheck, NewsSource
from .serializers import (
    NewsCheckSerializer,
    NewsSourceSerializer,
    PredictRequestSerializer,
)
from .source_utils import get_or_create_source
from .validators import validate_body, validate_title


class PredictView(APIView):
    """
    POST /api/predict/

    Receives title, text, domain (optional) and device_id.
    Calls the model on HuggingFace Space, resolves the news source,
    saves the result in DB and returns it.

    Request body:
        {
            "title": "...",
            "text": "...",
            "domain": "bbc.com",     <- extracted from page URL by the extension
            "device_id": "uuid"
        }

    Response:
        {
            "label": "FAKE" | "REAL",
            "confidence": 0.94,
            "probas": {"REAL": 0.06, "FAKE": 0.94},
            "check_id": 1,
            "news_source": {
                "id": 1,
                "name": "BBC",
                "domain": "bbc.com",
                "logo_url": "https://...",
                "is_predefined": true
            }
        }
    """

    def post(self, request):
        # 1. Validate format
        serializer = PredictRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        title = data["title"]
        text = data["text"]
        domain = data.get("domain", "").strip() or None

        # 2. Validate content
        title_validation = validate_title(title)
        body_validation = validate_body(text)

        errors = title_validation.errors + body_validation.errors
        if errors:
            return Response(
                {"validation_errors": errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        warnings = title_validation.warnings + body_validation.warnings

        # 3. Get or create anonymous user
        user, _ = AnonymousUser.objects.get_or_create(id=data["device_id"])

        # 4. Resolve news source from domain (if provided)
        news_source = None
        if domain:
            news_source = get_or_create_source(domain)

        # 5. Call the model
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

        # 6. Save to database
        check = NewsCheck.objects.create(
            user=user,
            title=title,
            text=text,
            news_source=news_source,
            label=result["label"],
            confidence=result["confidence"],
        )

        # 7. Return result
        response_data = {
            "label": result["label"],
            "confidence": result["confidence"],
            "probas": result["probas"],
            "check_id": check.id,
            "news_source": (
                NewsSourceSerializer(news_source).data if news_source else None
            ),
        }
        if warnings:
            response_data["warnings"] = warnings

        return Response(response_data, status=status.HTTP_200_OK)


class HistoryView(APIView):
    """
    GET /api/history/

    Returns paginated list of news articles analyzed by the user.
    Each item includes the full NewsSource object (name + logo).
    Requires header: X-Device-ID

    Query params:
        page      (optional) — page number, default 1
        page_size (optional) — results per page, default 10, max 50

    Response:
        {
            "count": 45,
            "total_pages": 5,
            "current_page": 1,
            "results": [
                {
                    "id": 1,
                    "title": "...",
                    "news_source": {"name": "BBC", "logo_url": "...", ...},
                    "label": "REAL",
                    "confidence": 0.94,
                    "created_at": "..."
                },
                ...
            ]
        }
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
            return Response(
                {"count": 0, "total_pages": 0, "current_page": 1, "results": []},
                status=status.HTTP_200_OK,
            )

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1

        try:
            page_size = min(50, max(1, int(request.query_params.get("page_size", 10))))
        except ValueError:
            page_size = 10

        checks = user.checks.select_related("news_source").all()
        total = checks.count()
        total_pages = max(1, -(-total // page_size))

        start = (page - 1) * page_size
        end = start + page_size
        page_checks = checks[start:end]

        serializer = NewsCheckSerializer(page_checks, many=True)

        return Response(
            {
                "count": total,
                "total_pages": total_pages,
                "current_page": page,
                "results": serializer.data,
            }
        )


class SourceStatsView(APIView):
    """
    GET /api/sources/

    Returns the top 5 most reliable news sources for the user,
    including the full NewsSource object (name + logo) for each.

    Ordering criteria:
        1. Primary:   number of articles labeled REAL (descending)
        2. Tiebreak:  average confidence of REAL articles (descending)

    Requires header: X-Device-ID

    Response:
        [
            {
                "news_source": {
                    "id": 1,
                    "name": "BBC",
                    "domain": "bbc.com",
                    "logo_url": "https://...",
                    "is_predefined": true
                },
                "total": 10,
                "real": 8,
                "fake": 2,
                "real_confidence_avg": 0.85,
                "reliability_pct": 80.0
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

        checks = user.checks.filter(news_source__isnull=False).select_related(
            "news_source"
        )

        if not checks.exists():
            return Response([], status=status.HTTP_200_OK)

        # Group by news_source
        stats = {}
        for check in checks:
            src_id = check.news_source.id
            if src_id not in stats:
                stats[src_id] = {
                    "news_source": check.news_source,
                    "total": 0,
                    "real": 0,
                    "fake": 0,
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
            total = src_data["total"]

            real_confidence_avg = (
                round(src_data["real_confidence_sum"] / real_count, 4)
                if real_count > 0
                else 0.0
            )

            result.append(
                {
                    "news_source": NewsSourceSerializer(src_data["news_source"]).data,
                    "total": total,
                    "real": real_count,
                    "fake": src_data["fake"],
                    "real_confidence_avg": real_confidence_avg,
                    "reliability_pct": round(real_count / total * 100, 1),
                }
            )

        result.sort(
            key=lambda x: (x["real"], x["real_confidence_avg"]),
            reverse=True,
        )

        return Response(result[:5])


class SourceLookupView(APIView):
    """
    GET /api/sources/lookup/?domain=bbc.com

    Called by the Chrome extension before predicting to check if a domain
    is already registered in the system and retrieve its name and logo.

    If the domain is not found, returns null so the extension knows
    it will be created at prediction time via Clearbit.

    Response (found):
        {
            "id": 1,
            "name": "BBC",
            "domain": "bbc.com",
            "logo_url": "https://...",
            "is_predefined": true
        }

    Response (not found):
        null
    """

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
    """
    GET /api/similar/

    Searches for news articles in the system whose title is similar
    to the one provided, combining two complementary PostgreSQL strategies:

      - Trigram similarity (pg_trgm): detects titles that share similar
        character sequences, handling typos and partial word matches.

      - Full-text search (tsvector/tsquery): finds titles that are
        semantically related even when vocabulary differs, by applying
        linguistic stemming (e.g. "loses" and "defeat" both relate to
        the concept of losing).

    Both use GIN indexes. Results are ranked by the sum of both scores
    so that articles matching both strategies rank highest.
    The exact title searched is excluded from results.

    Query params:
        title    (required) — title to compare against
        min_sim  (optional) — minimum threshold for both mechanisms, default 0.25

    Response:
        [
            {
                "title": "Trump loses the election",
                "source_name": "BBC",
                "source_logo": "https://...",
                "label": "FAKE",
                "similarity": 0.72,
                "fts_rank": 0.31,
                "match_type": "trigram+fulltext" | "trigram" | "fulltext"
            },
            ...
        ]
    """

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
            cursor.execute(
                """
                SELECT
                    nc.title,
                    ns.name AS source_name,
                    ns.logo_url AS source_logo,
                    nc.label,
                    ROUND(COALESCE(similarity(nc.title, %s), 0)::numeric, 4) AS trgm_sim,
                    ROUND(COALESCE(
                        ts_rank(to_tsvector('english', nc.title),
                        plainto_tsquery('english', %s)), 0
                    )::numeric, 4) AS fts_rank,
                    CASE
                        WHEN similarity(nc.title, %s) >= %s
                         AND to_tsvector('english', nc.title) @@ plainto_tsquery('english', %s)
                        THEN 'trigram+fulltext'
                        WHEN similarity(nc.title, %s) >= %s
                        THEN 'trigram'
                        ELSE 'fulltext'
                    END AS match_type
                FROM news_checks nc
                LEFT JOIN news_sources ns ON nc.news_source_id = ns.id
                WHERE
                    nc.title != %s
                    AND (
                        similarity(nc.title, %s) >= %s
                        OR ts_rank(
                            to_tsvector('english', nc.title),
                            plainto_tsquery('english', %s)
                        ) >= %s
                    )
                ORDER BY (
                    COALESCE(similarity(nc.title, %s), 0)
                    + COALESCE(ts_rank(
                        to_tsvector('english', nc.title),
                        plainto_tsquery('english', %s)
                    ), 0)
                ) DESC
                LIMIT 5
                """,
                [
                    title,  # trgm_sim SELECT
                    title,  # fts_rank SELECT
                    title,
                    min_sim,  # CASE trigram+fulltext
                    title,  # CASE fts check
                    title,
                    min_sim,  # CASE trigram only
                    title,  # WHERE exclude exact match
                    title,
                    min_sim,  # WHERE trgm condition
                    title,
                    min_sim,  # WHERE fts condition
                    title,  # ORDER BY trgm
                    title,  # ORDER BY fts
                ],
            )
            rows = cursor.fetchall()

        results = [
            {
                "title": row[0],
                "source_name": row[1],
                "source_logo": row[2],
                "label": row[3],
                "similarity": float(row[4]),
                "fts_rank": float(row[5]),
                "match_type": row[6],
            }
            for row in rows
        ]

        return Response(results)
