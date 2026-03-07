from django.urls import path

from .views import CuentaAperturaView, CuentaListView, TransaccionListView, ping

urlpatterns = [
    path('cuentas/', CuentaListView.as_view(), name='ahorro_cuentas_list'),
    path('movimientos/', TransaccionListView.as_view(), name='ahorro_movimientos_list'),
    path('aperturar/', CuentaAperturaView.as_view(), name='ahorro_aperturar'),
    path('ping/', ping),
]
