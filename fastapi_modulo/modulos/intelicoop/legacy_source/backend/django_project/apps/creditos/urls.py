from django.urls import path

from .views import (
    CreditoListCreateView,
    CreditoRetrieveUpdateDestroyView,
    HistorialPagoListCreateView,
    HistorialPagoRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("", CreditoListCreateView.as_view(), name="credito_list_create"),
    path("<int:pk>/", CreditoRetrieveUpdateDestroyView.as_view(), name="credito_detail"),
    path("pagos/", HistorialPagoListCreateView.as_view(), name="historial_pago_list_create"),
    path("pagos/<int:pk>/", HistorialPagoRetrieveUpdateDestroyView.as_view(), name="historial_pago_detail"),
]
