from rest_framework import serializers

from .models import Cuenta, Transaccion


class CuentaSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.nombre", read_only=True)

    class Meta:
        model = Cuenta
        fields = ("id", "socio", "socio_nombre", "tipo", "saldo", "fecha_creacion")
        read_only_fields = ("id", "fecha_creacion", "socio_nombre")

    def validate_saldo(self, value):
        if value < 0:
            raise serializers.ValidationError("El saldo inicial no puede ser negativo.")
        return value


class TransaccionSerializer(serializers.ModelSerializer):
    cuenta_id = serializers.IntegerField(source="cuenta.id", read_only=True)

    class Meta:
        model = Transaccion
        fields = ("id", "cuenta", "cuenta_id", "monto", "tipo", "fecha")
        read_only_fields = ("id", "fecha", "cuenta_id")

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return value
