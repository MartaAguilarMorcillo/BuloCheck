from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import AnonymousUser, NewsCheck
from .serializers import PredictRequestSerializer, NewsCheckSerializer
from .ml import predict_news


class PredictView(APIView):
    """
    POST /api/predict/

    Recibe title, text, source (opcional) y device_id.
    Llama al modelo en HuggingFace, guarda el resultado en BD y lo devuelve.

    Body JSON:
        {
            "title": "...",
            "text": "...",
            "source": "elpais.com",   ← opcional
            "device_id": "uuid-del-navegador"
        }

    Respuesta:
        {
            "label": "FAKE",
            "confidence": 0.94,
            "probas": {"REAL": 0.06, "FAKE": 0.94},
            "check_id": 12
        }
    """

    def post(self, request):
        # 1. Validar entrada
        serializer = PredictRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        device_id = data["device_id"]
        title = data["title"]
        text = data["text"]
        source = data.get("source", None)

        # 2. Obtener o crear usuario anónimo por device_id
        user, _ = AnonymousUser.objects.get_or_create(id=device_id)

        # 3. Llamar al modelo
        try:
            result = predict_news(title=title, text=text)
        except RuntimeError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 4. Guardar en base de datos
        check = NewsCheck.objects.create(
            user=user,
            title=title,
            text=text,
            source=source or None,
            label=result["label"],
            confidence=result["confidence"],
        )

        # 5. Devolver resultado
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

    Devuelve el historial de noticias analizadas por el usuario.
    El device_id se manda como header: X-Device-ID

    Respuesta:
        [
            {
                "id": 1,
                "title": "...",
                "label": "FAKE",
                "confidence": 0.94,
                "source": "elpais.com",
                "created_at": "2024-05-14T10:23:00Z"
            },
            ...
        ]
    """

    def get(self, request):
        device_id = request.headers.get("X-Device-ID")
        if not device_id:
            return Response(
                {"error": "Falta el header X-Device-ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = AnonymousUser.objects.get(id=device_id)
        except (AnonymousUser.DoesNotExist, Exception):
            # Si el usuario no existe devolvemos historial vacío
            return Response([], status=status.HTTP_200_OK)

        checks = user.checks.all()
        serializer = NewsCheckSerializer(checks, many=True)
        return Response(serializer.data)


class SourceStatsView(APIView):
    """
    GET /api/sources/

    Devuelve estadísticas por fuente: cuántas noticias reales y falsas
    se han detectado en cada fuente, y el porcentaje de fiabilidad.
    El device_id se manda como header: X-Device-ID

    Respuesta:
        [
            {
                "source": "elpais.com",
                "total": 10,
                "real": 8,
                "fake": 2,
                "reliability_pct": 80.0   ← % de noticias REAL sobre el total
            },
            ...
        ]
    """

    def get(self, request):
        device_id = request.headers.get("X-Device-ID")
        if not device_id:
            return Response(
                {"error": "Falta el header X-Device-ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = AnonymousUser.objects.get(id=device_id)
        except (AnonymousUser.DoesNotExist, Exception):
            return Response([], status=status.HTTP_200_OK)

        # Solo las noticias con fuente informada
        checks = user.checks.filter(source__isnull=False).exclude(source="")

        # Agrupar manualmente por fuente
        stats = {}
        for check in checks:
            src = check.source
            if src not in stats:
                stats[src] = {"source": src, "total": 0, "real": 0, "fake": 0}
            stats[src]["total"] += 1
            if check.label == "REAL":
                stats[src]["real"] += 1
            else:
                stats[src]["fake"] += 1

        # Calcular porcentaje de fiabilidad y ordenar de más a menos fiable
        result = []
        for src_data in stats.values():
            src_data["reliability_pct"] = round(
                src_data["real"] / src_data["total"] * 100, 1
            )
            result.append(src_data)

        result.sort(key=lambda x: x["reliability_pct"], reverse=True)
        return Response(result)
