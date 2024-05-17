from rest_framework import pagination
from rest_framework.response import Response
import datetime
class CustomLimitOffsetPagination(pagination.LimitOffsetPagination):
    """
    limit: Specifies the number of items to include per page (e.g., /api/mymodels?limit=20).
    offset: Specifies the starting position in the result set (e.g., /api/mymodels?offset=40).
    """

    default_limit = 1000
    limit_query_param = "limit"
    offset_query_param = "offsett"
    max_limit = 1000
    page_size = 1000    


class CustomPagePagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return {
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "count": self.page.paginator.count,
            "limit": self.page_size,
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            "results": data,
        }


class CustomCursorPagination(pagination.CursorPagination):
    """
    this pagination is used to accept when it's needed to terms and conditon showing and no need to skip
    """

    page_size = 2
    cursor_query_param = "c"
    ordering = "-id"

class LargeResultsSetPagination(pagination.PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000
    def get_paginated_response(self, data):
        return {
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "count": self.page.paginator.count,
            "limit": self.page_size,
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            "results": data,
        }