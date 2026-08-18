from django.contrib import admin

from .models import Click, Link


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ("code", "target_url", "created_at", "expires_at")
    search_fields = ("code", "target_url")


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ("link", "created_at", "referrer")
    list_filter = ("created_at",)
