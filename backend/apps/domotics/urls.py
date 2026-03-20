from django.urls import path

from . import views

app_name = "domotics"

urlpatterns = [
    # Property devices
    path(
        "properties/<int:property_id>/devices/",
        views.PropertyDevicesView.as_view(),
        name="property-devices",
    ),
    path(
        "properties/<int:property_id>/access-codes/",
        views.ActiveAccessCodesView.as_view(),
        name="property-access-codes",
    ),
    path(
        "properties/<int:property_id>/noise-alerts/",
        views.NoiseAlertsView.as_view(),
        name="property-noise-alerts",
    ),
    path(
        "properties/<int:property_id>/devices/onboard/",
        views.DeviceOnboardView.as_view(),
        name="device-onboard",
    ),
    # Individual devices
    path(
        "devices/<int:device_id>/",
        views.DeviceDetailView.as_view(),
        name="device-detail",
    ),
    path(
        "devices/<int:device_id>/<str:action>/",
        views.LockControlView.as_view(),
        name="lock-control",
    ),
    path(
        "devices/<int:device_id>/temperature/",
        views.ThermostatControlView.as_view(),
        name="thermostat-control",
    ),
    # Guest access
    path(
        "reservations/<int:reservation_id>/access/",
        views.GuestAccessInfoView.as_view(),
        name="guest-access",
    ),
    # Webhooks
    path(
        "webhooks/seam/",
        views.SeamWebhookView.as_view(),
        name="seam-webhook",
    ),
]
