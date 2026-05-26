from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    HistoryView, PredictView, RegisterView,
    SimilarNewsView, SourceLookupView, SourceStatsView,
)

urlpatterns = [
    # Auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # App
    path("predict/", PredictView.as_view(), name="predict"),
    path("history/", HistoryView.as_view(), name="history"),
    path("sources/", SourceStatsView.as_view(), name="sources"),
    path("sources/lookup/", SourceLookupView.as_view(), name="sources-lookup"),
    path("similar/", SimilarNewsView.as_view(), name="similar"),
]