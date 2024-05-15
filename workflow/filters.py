import logging
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend, SearchFilter

_l = logging.getLogger('workflow')

class WorkflowQueryFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = request.query_params.get('query', None)

        if query:

            pieces = query.split(' ')

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
    def get_search_terms(self, request):
        terms = super().get_search_terms(request)
        for i in range(len(terms)):
            if terms[i]:
                terms[i] = f'\\m{terms[i]}\\M'
        return terms
