from rest_framework import serializers

from .models import Credito, HistorialPago


class CreditoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.nombre", read_only=True)

    class Meta:
        model = Credito
        fields = (
            "id",
            "socio",
            "socio_nombre",
            "monto",
            "plazo",
            "ingreso_mensual",
            "deuda_actual",
            "antiguedad_meses",
            "estado",
            "fecha_creacion",
        )
        read_only_fields = ("id", "fecha_creacion", "socio_nombre")

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return value

    def validate_plazo(self, value):
        if value <= 0:
            raise serializers.ValidationError("El plazo debe ser mayor a 0.")
        return value

    def validate_ingreso_mensual(self, value):
        if value <= 0:
            raise serializers.ValidationError("El ingreso mensual debe ser mayor a 0.")
        return value

    def validate_deuda_actual(self, value):
        if value < 0:
            raise serializers.ValidationError("La deuda actual no puede ser negativa.")
        return value

    def validate_antiguedad_meses(self, value):
        if value < 0:
            raise serializers.ValidationError("La antiguedad no puede ser negativa.")
        return value

    def validate(self, attrs):
        ingreso = attrs.get("ingreso_mensual")
        deuda = attrs.get("deuda_actual")

        if ingreso is not None and deuda is not None and deuda > ingreso:
            raise serializers.ValidationError(
                {"deuda_actual": "La deuda actual no puede ser mayor al ingreso mensual."}
            )
        return attrs


class HistorialPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPago
        fields = "__all__"

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto del pago debe ser mayor a 0.")
        return value
