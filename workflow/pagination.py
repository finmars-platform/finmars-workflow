import logging
import sys
import time

from django.core.paginator import InvalidPage
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.settings import api_settings

_l = logging.getLogger('workflow')


class PageNumberPaginationExt(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = api_settings.PAGE_SIZE * 10

    def post_paginate_queryset(self, queryset, request, view=None):

        start_time = time.time()

        page_size = request.data.get('page_size', self.page_size)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.data.get('page', 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        # _l.debug('post_paginate_queryset page_number %s' % page_number)
        # _l.debug('post_paginate_queryset page_size %s' % page_size)
        # _l.debug('post_paginate_queryset django_paginator_class %s' % self.django_paginator_class)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request

        _l.debug('post_paginate_queryset before list page')

        list_page_st = time.perf_counter()

        res = list(self.page)

        _l.debug('res %s' % len(res))

        _l.debug('post_paginate_queryset list page done: %s', "{:3.3f}".format(time.perf_counter() - list_page_st))

        return res
