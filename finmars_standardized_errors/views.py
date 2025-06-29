from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from finmars_standardized_errors.models import ErrorRecord
from finmars_standardized_errors.serializers import ErrorRecordSerializer


class ErrorRecordViewSet(ModelViewSet):
    queryset = ErrorRecord.objects.all()
    serializer_class = ErrorRecordSerializer
    permission_classes = [
        IsAuthenticated
    ]
    filter_backends = []
    ordering_fields = ['created']

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        query = request.GET.get('query', None)

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) | Q(message__icontains=query) | Q(details_data__icontains=query) | Q(
                    url__icontains=query) | Q(
                    status_code__icontains=query) | Q(
                    created__icontains=query))

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
