from django.urls import path

from .views import SocioListView, ping

urlpatterns = [
    path('', SocioListView.as_view(), name='socio_list'),
    path('ping/', ping),
]
