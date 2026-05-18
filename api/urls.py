from django.urls import path

from .views import HistoryView, PredictView, SourceStatsView

urlpatterns = [
    path("predict/", PredictView.as_view(), name="predict"),
    path("history/", HistoryView.as_view(), name="history"),
    path("sources/", SourceStatsView.as_view(), name="sources"),
]
