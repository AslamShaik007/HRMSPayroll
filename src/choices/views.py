from choices.models import Choices
from choices.serializers import ChoicesSerializer
from core.views import AbstractListAPIView


class ListChoicesView(AbstractListAPIView):
    """
    AJAY, 04.05.2023
    """

    serializer_class = ChoicesSerializer
    filterset_fields = ["choice_type__slug", "choice_type__company"]
    queryset = Choices.objects.filter(is_active=True)
