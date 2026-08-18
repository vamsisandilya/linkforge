from django.db import models
from django.utils import timezone


class Link(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    target_url = models.URLField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} -> {self.target_url}"

    def is_expired(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()


class Click(models.Model):
    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name="clicks")
    created_at = models.DateTimeField(auto_now_add=True)
    referrer = models.CharField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        # Index tuned for the analytics query (clicks for a link, over time).
        indexes = [models.Index(fields=["link", "created_at"])]

    def __str__(self):
        return f"click on {self.link.code} @ {self.created_at:%Y-%m-%d}"
