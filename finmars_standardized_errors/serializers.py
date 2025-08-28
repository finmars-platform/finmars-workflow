from rest_framework import serializers

from finmars_standardized_errors.models import ErrorRecord


class ErrorRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorRecord
        fields = ["id", "url", "username", "message", "status_code", "notes", "created", "details"]
