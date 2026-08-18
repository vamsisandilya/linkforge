from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache import get_cached_target, set_cached_target
from .models import Link
from .ratelimit import is_rate_limited
from .serializers import LinkSerializer
from .tasks import record_click


def _client_key(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "anon")


class LinkViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer
    lookup_field = "code"

    def create(self, request, *args, **kwargs):
        if is_rate_limited(_client_key(request), settings.CREATE_RATE_LIMIT, 60):
            return Response({"detail": "Rate limit exceeded."}, status=429)
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def stats(self, request, code=None):
        link = self.get_object()
        clicks = link.clicks
        days = request.query_params.get("days")
        if days is not None:
            since = timezone.now() - timedelta(days=int(days))
            clicks = clicks.filter(created_at__gte=since)
        by_day = list(
            clicks.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        top_referrers = list(
            clicks.exclude(referrer="")
            .values("referrer")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        return Response(
            {
                "code": link.code,
                "total_clicks": clicks.count(),
                "clicks_by_day": by_day,
                "top_referrers": top_referrers,
            }
        )


class RedirectView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, code):
        target = get_cached_target(code)
        if target is None:
            try:
                link = Link.objects.get(code=code)
            except Link.DoesNotExist:
                return Response({"detail": "Not found."}, status=404)
            if link.is_expired():
                return Response({"detail": "Link expired."}, status=410)
            target = link.target_url
            set_cached_target(code, target)

        record_click.delay(
            code,
            request.META.get("HTTP_REFERER", ""),
            request.META.get("HTTP_USER_AGENT", ""),
        )
        return redirect(target)
