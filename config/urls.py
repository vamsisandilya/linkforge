from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from links.views import LinkViewSet, RedirectView

router = DefaultRouter()
router.register("links", LinkViewSet, basename="link")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    # Redirect hot path — keep LAST so /admin/ and /api/ win first.
    path("<slug:code>/", RedirectView.as_view(), name="redirect"),
    path("<slug:code>", RedirectView.as_view()),
]
