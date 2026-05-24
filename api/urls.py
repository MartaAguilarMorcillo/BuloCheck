from django.urls import path

from .views import HistoryView, PredictView, SimilarNewsView, SourceLookupView, SourceStatsView

urlpatterns = [
    path("predict/", PredictView.as_view(), name="predict"),
    path("history/", HistoryView.as_view(), name="history"),
    path("sources/", SourceStatsView.as_view(), name="sources"),
    path("sources/lookup/", SourceLookupView.as_view(), name="sources-lookup"),
    path("similar/", SimilarNewsView.as_view(), name="similar"),
]