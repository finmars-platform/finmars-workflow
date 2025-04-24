import logging
import sys
import time

from django.core.paginator import InvalidPage
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.settings import api_settings

_l = logging.getLogger("workflow")


class PageNumberPaginationExt(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = api_settings.PAGE_SIZE * 10

    def post_paginate_queryset(self, queryset, request, view=None):
        start_time = time.time()

        qs = super().paginate_queryset(queryset, request, view)

        # _l.debug('post_paginate_queryset before list page')

        list_page_st = time.perf_counter()

        # _l.debug('res %s' % len(qs))

        # _l.debug('post_paginate_queryset list page done: %s', "{:3.3f}".format(time.perf_counter() - list_page_st))
        return qs
