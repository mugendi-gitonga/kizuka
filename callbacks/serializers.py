from rest_framework import serializers

from payins.models import DepositRequest
from payouts.models import PayoutRequest


class DepositCallbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = DepositRequest
        fields = [
            "alias_id",
            "currency",
            "amount",
            "charge",
            "taxes",
            "net_amount",
            "phone_number",
            "status",
            "message",
            "reference",
            "narration",
            "provider",
            "provider_reference",
            "created_at",
            "updated_at",
        ]


class PayoutCallbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayoutRequest
        fields = [
            "alias_id",
            "currency",
            "amount",
            "charge",
            "taxes",
            "total_amount",
            "phone_number",
            "status",
            "message",
            "reference",
            "narration",
            "provider",
            "provider_reference",
            "created_at",
            "updated_at",
        ]