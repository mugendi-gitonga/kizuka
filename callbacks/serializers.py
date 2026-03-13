from rest_framework import serializers

from payins.models import DepositRequest
from payouts.models import PayoutRequest


class DepositCallbackSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    class Meta:
        model = DepositRequest
        fields = [
            "id",
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
    
    def get_id(self, obj):
        return obj.alias


class PayoutCallbackSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = PayoutRequest
        fields = [
            "id",
            "currency",
            "amount",
            "charge",
            "taxes",
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
    
    def get_id(self, obj):
        return obj.alias
    
    def get_total_amount(self, obj):
        return obj.total_amount