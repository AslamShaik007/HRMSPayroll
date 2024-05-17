from rest_framework import serializers

from .models import Report


class EmployeeReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "name",
            "file",
            "category",
            "status",
            "notes",
            "is_deleted",
            "content_type",
        ]
