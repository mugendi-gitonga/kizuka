from rest_framework import serializers

from payins.models import DepositRequest


class DepositCallbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = DepositRequest
        fields = [
            "alias_id",
            "currency"
            "amount",
            "charge",
            "taxes",
            "net_amount",
            "phone_number",
            "status",
            "reference",
            "narration",
            "provider",
            "provider_reference",
            "created_at",
            "updated_at",
        ]