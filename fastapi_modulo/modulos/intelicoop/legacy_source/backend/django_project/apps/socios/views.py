from django.http import JsonResponse
from rest_framework import generics

from apps.authentication.permissions import IsAuditorOrHigher

from .models import Socio
from .serializers import SocioSerializer

def ping(_request):
    return JsonResponse({'app': 'socios', 'status': 'ok'})


class SocioListView(generics.ListAPIView):
    queryset = Socio.objects.all()
    serializer_class = SocioSerializer
    permission_classes = [IsAuditorOrHigher]
