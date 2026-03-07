from rest_framework import generics

from apps.authentication.permissions import IsAuditorOrHigher

from .models import Credito, HistorialPago
from .serializers import CreditoSerializer, HistorialPagoSerializer


class CreditoListCreateView(generics.ListCreateAPIView):
    queryset = Credito.objects.select_related("socio").all()
    serializer_class = CreditoSerializer
    permission_classes = [IsAuditorOrHigher]


class CreditoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Credito.objects.select_related("socio").all()
    serializer_class = CreditoSerializer
    permission_classes = [IsAuditorOrHigher]


class HistorialPagoListCreateView(generics.ListCreateAPIView):
    queryset = HistorialPago.objects.select_related("credito").all()
    serializer_class = HistorialPagoSerializer
    permission_classes = [IsAuditorOrHigher]


class HistorialPagoRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = HistorialPago.objects.select_related("credito").all()
    serializer_class = HistorialPagoSerializer
    permission_classes = [IsAuditorOrHigher]
