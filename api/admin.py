from django.contrib import admin

from .models import AnonymousUser, NewsCheck


@admin.register(AnonymousUser)
class AnonymousUserAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at"]
    ordering = ["-created_at"]


@admin.register(NewsCheck)
class NewsCheckAdmin(admin.ModelAdmin):
    list_display = ["id", "label", "confidence", "source", "title_short", "created_at"]
    list_filter = ["label", "source"]
    search_fields = ["title", "source"]
    ordering = ["-created_at"]

    def title_short(self, obj):
        return obj.title[:60]

    title_short.short_description = "Title"
