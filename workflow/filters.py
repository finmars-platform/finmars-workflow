import logging
from datetime import datetime, timedelta

import django_filters
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend, SearchFilter

_l = logging.getLogger("workflow")


class WorkflowQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get("query", None)

        if query:

            pieces = query.split(" ")

            id_q = Q()
            name_q = Q()
            user_code_q = Q()
            created_q = Q()
            status_q = Q()

            for piece in pieces:
                id_q.add(Q(id__icontains=piece), Q.AND)
                name_q.add(Q(name__icontains=piece), Q.AND)
                user_code_q.add(Q(user_code__icontains=piece), Q.AND)
                created_q.add(Q(created__icontains=piece), Q.AND)
                status_q.add(Q(status__icontains=piece), Q.AND)

            options = Q()

            options.add(id_q, Q.OR)
            options.add(name_q, Q.OR)
            options.add(user_code_q, Q.OR)
            options.add(created_q, Q.OR)
            options.add(status_q, Q.OR)

            return queryset.filter(options)

        return queryset


class WholeWordsSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, "search_fields", [])
        search_terms = self.get_search_terms(request)

        queries = Q()
        for term in search_terms:
            term_query = Q()
            for field in search_fields:
                term_query |= Q(**{f"{field}__regex": rf"\m{term}\M"})
            queries &= term_query

        return queryset.filter(queries)


class CharFilter(django_filters.CharFilter):
    def __init__(self, *args, **kwargs):
        kwargs["lookup_expr"] = "icontains"
        super().__init__(*args, **kwargs)


class WorkflowSearchParamFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        date_from = request.query_params.get("date_from", None)
        date_to = request.query_params.get("date_to", None)
        status = request.query_params.get("status", None)
        is_manager = request.query_params.get("is_manager", None)

        if date_from:
            date = datetime.strptime(date_from, "%Y-%m-%d")
            queryset = queryset.filter(created__gte=date)

        if date_to:
            date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(
                days=1, microseconds=-1
            )
            queryset = queryset.filter(created__lte=date)

        if status:
            status_list = status.split(",")
            queryset = queryset.filter(status__in=status_list)

        if is_manager:
            queryset = queryset.filter(is_manager=is_manager)

        return queryset
