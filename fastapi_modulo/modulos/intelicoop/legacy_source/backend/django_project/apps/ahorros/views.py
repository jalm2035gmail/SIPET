from django.http import JsonResponse
from rest_framework import generics

from apps.authentication.permissions import IsAuditorOrHigher

from .models import Cuenta, Transaccion
from .serializers import CuentaSerializer, TransaccionSerializer


def ping(_request):
    return JsonResponse({'app': 'ahorros', 'status': 'ok'})


class CuentaListView(generics.ListAPIView):
    queryset = Cuenta.objects.select_related("socio").all()
    serializer_class = CuentaSerializer
    permission_classes = [IsAuditorOrHigher]


class TransaccionListView(generics.ListAPIView):
    queryset = Transaccion.objects.select_related("cuenta").all()
    serializer_class = TransaccionSerializer
    permission_classes = [IsAuditorOrHigher]


class CuentaAperturaView(generics.CreateAPIView):
    queryset = Cuenta.objects.select_related("socio").all()
    serializer_class = CuentaSerializer
    permission_classes = [IsAuditorOrHigher]
