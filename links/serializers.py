from rest_framework import serializers

from .codes import unique_code
from .models import Link


class LinkSerializer(serializers.ModelSerializer):
    short_url = serializers.SerializerMethodField()

    class Meta:
        model = Link
        fields = ["id", "code", "target_url", "short_url", "created_at", "expires_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"code": {"required": False}}

    def get_short_url(self, obj):
        request = self.context.get("request")
        path = f"/{obj.code}"
        return request.build_absolute_uri(path) if request else path

    def create(self, validated_data):
        if not validated_data.get("code"):
            validated_data["code"] = unique_code()
        return super().create(validated_data)
