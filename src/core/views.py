from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.views import APIView


class AbstractAPIView(APIView):
    """
    Abstract Class for APIView
    """

    pass


class AbstractListAPIView(ListAPIView):
    """
    AJAY, 17.01.2023
    """

    def filter_queryset(self, queryset):
        """
        It filters the queryset to only include objects that have is_deleted set to False

        :param queryset: The queryset that will be used to retrieve the objects that this view will
        display
        :return: The queryset is being returned.
        """
        queryset = queryset.filter(is_deleted=False)
        return super().filter_queryset(queryset)


class AbstractListCreateAPIView(ListCreateAPIView):
    """
    AJAY, 17.01.2023
    """

    def filter_queryset(self, queryset):
        """
        It filters the queryset to only include objects that have is_deleted set to False

        :param queryset: The queryset that will be used to retrieve the objects that this view will
        display
        :return: The queryset is being returned.
        """
        queryset = queryset.filter(is_deleted=False)
        return super().filter_queryset(queryset)


class AbstractRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    """
    AJAY, 17.01.2023
    """

    def filter_queryset(self, queryset):
        """
        It filters the queryset to only include objects that have is_deleted set to False

        :param queryset: The queryset that will be used to retrieve the object that the view will
        display
        :return: The queryset is being returned.
        """
        queryset = queryset.filter(is_deleted=False)
        return super().filter_queryset(queryset)
