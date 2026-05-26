from django.contrib import admin
from .models import User, NewsCheck, NewsSource


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "is_active", "is_staff", "created_at"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["email"]
    ordering = ["-created_at"]


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "domain", "is_predefined", "created_at"]
    list_filter = ["is_predefined"]
    search_fields = ["name", "domain"]
    ordering = ["name"]


@admin.register(NewsCheck)
class NewsCheckAdmin(admin.ModelAdmin):
    list_display = ["id", "label", "confidence", "news_source", "title_short", "created_at"]
    list_filter = ["label", "news_source"]
    search_fields = ["title", "news_source__name", "news_source__domain"]
    ordering = ["-created_at"]
    filter_horizontal = ["users"]

    def title_short(self, obj):
        return obj.title[:60]
    title_short.short_description = "Title"