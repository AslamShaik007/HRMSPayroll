from rest_framework import serializers

from choices.models import Choices, ChoiceType


class ChoiceTypeSerializer(serializers.ModelSerializer):
    """
    AJAY, 04.05.2023
    """

    class Meta:
        model = ChoiceType
        fields = "__all__"


class ChoicesSerializer(serializers.ModelSerializer):
    """
    AJAY, 04.05.2023
    """

    class Meta:
        model = Choices
        fields = "__all__"
