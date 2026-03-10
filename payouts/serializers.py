from rest_framework import serializers

from payouts.models import PayoutRequest

from utils import check_phone_number

class PayoutInitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = [
            "country",
            "currency",
            "amount",
            "phone_number",
            "reference",
            "narration",
            "provider"
        ]

    def validate_amount(self, value):
        if value < 10 and self.initial_data.get("currency", "KES") == "KES":
            raise serializers.ValidationError("Amount must be at least 10.")
        return value

    def validate(self, data):
        """
        Object-level validation to handle cross-field logic.
        """
        phone_number = data.get("phone_number")
        country = data.get("country", "KE")  # Use 'KE' as fallback

        if len(phone_number) < 10:
            raise serializers.ValidationError(
                {"phone_number": "Phone number must be at least 10 digits long."}
            )

        try:
            # Assuming check_phone_number formats the number for M-Pesa/IntaSend
            data["phone_number"] = check_phone_number(phone_number, country)
        except Exception as e:
            raise serializers.ValidationError(
                {"phone_number": f"Invalid format for {country}"}
            )
        return data


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = "__all__"
        exclude = [
            "id",
            "business",
            "tracking_id",
            "tracking_id_2",
            "init_response",
            "callback_response",
        ]
