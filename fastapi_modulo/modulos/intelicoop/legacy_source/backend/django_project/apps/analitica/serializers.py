from decimal import Decimal

from rest_framework import serializers

from .models import (
    Campania,
    Prospecto,
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoScoring,
    ResultadoSegmentacionSocio,
)


class CampaniaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campania
        fields = "__all__"
        read_only_fields = ("id", "fecha_creacion")

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({"fecha_fin": "La fecha fin no puede ser menor que la fecha inicio."})
        return attrs


class ProspectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prospecto
        fields = "__all__"
        read_only_fields = ("id", "fecha_creacion")

    def validate_score_propension(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError("El score_propension debe estar entre 0 y 1.")
        return value


class ResultadoScoringSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoScoring
        fields = "__all__"
        read_only_fields = ("id", "request_id", "fecha_creacion")

    def validate_score(self, value):
        if value < 0 or value > 1:
            raise serializers.ValidationError("El score debe estar entre 0 y 1.")
        return value

    def validate_recomendacion(self, value):
        allowed = {"aprobar", "evaluar", "rechazar"}
        if value not in allowed:
            raise serializers.ValidationError("La recomendacion debe ser aprobar, evaluar o rechazar.")
        return value


class ScoringEvaluateSerializer(serializers.Serializer):
    ingreso_mensual = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    deuda_actual = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    antiguedad_meses = serializers.IntegerField(min_value=0)
    persist = serializers.BooleanField(required=False, default=False)
    solicitud_id = serializers.CharField(required=False, allow_blank=True, max_length=120)
    credito = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    socio = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    model_version = serializers.CharField(required=False, allow_blank=True, max_length=60, default="weighted_score_v1")

    def validate(self, attrs):
        ingreso = attrs.get("ingreso_mensual")
        deuda = attrs.get("deuda_actual")
        if ingreso is not None and deuda is not None and deuda > ingreso:
            raise serializers.ValidationError(
                {"deuda_actual": "La deuda actual no puede ser mayor al ingreso mensual."}
            )
        return attrs


class ResultadoMoraTempranaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoMoraTemprana
        fields = "__all__"
        read_only_fields = ("id", "request_id", "fecha_creacion")


class MoraTempranaEvaluateSerializer(serializers.Serializer):
    credito = serializers.IntegerField(min_value=1)
    persist = serializers.BooleanField(required=False, default=True)
    fecha_corte = serializers.DateField(required=False)
    model_version = serializers.CharField(required=False, allow_blank=True, max_length=60, default="mora_temprana_v1")


class SegmentacionInteligenteRunSerializer(serializers.Serializer):
    metodo = serializers.ChoiceField(choices=["reglas", "clustering"], default="reglas")
    clusters = serializers.IntegerField(required=False, min_value=1, max_value=12, default=5)
    thresholds_json = serializers.CharField(required=False, allow_blank=False, max_length=255)
    thresholds_version = serializers.CharField(required=False, allow_blank=False, max_length=80)
    report_csv = serializers.CharField(required=False, allow_blank=False, max_length=255)
    dataset_csv = serializers.CharField(required=False, allow_blank=False, max_length=255)
    report_md = serializers.CharField(required=False, allow_blank=False, max_length=255)


class ResultadoSegmentacionSocioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoSegmentacionSocio
        fields = "__all__"
        read_only_fields = ("id", "request_id", "fecha_creacion")


class ReglaAsociacionProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReglaAsociacionProducto
        fields = "__all__"
        read_only_fields = ("id", "request_id", "fecha_creacion")
