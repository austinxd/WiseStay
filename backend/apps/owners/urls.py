from django.urls import path

from . import views

app_name = "owners"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.OwnerDashboardView.as_view(), name="dashboard"),
    # Properties
    path("properties/", views.OwnerPropertiesListView.as_view(), name="properties-list"),
    path("properties/<int:pk>/", views.OwnerPropertyDetailView.as_view(), name="property-detail"),
    path("properties/<int:pk>/performance/", views.PropertyPerformanceView.as_view(), name="property-performance"),
    path("properties/<int:pk>/occupancy/", views.OccupancyCalendarView.as_view(), name="property-occupancy"),
    path("properties/<int:pk>/devices/", views.OwnerDevicesView.as_view(), name="property-devices"),
    path("properties/<int:pk>/noise-alerts/", views.OwnerNoiseAlertsView.as_view(), name="property-noise-alerts"),
    # Reservations
    path("reservations/", views.OwnerReservationsView.as_view(), name="reservations-list"),
    path("reservations/<int:pk>/", views.OwnerReservationDetailView.as_view(), name="reservation-detail"),
    # Revenue
    path("revenue/", views.RevenueReportView.as_view(), name="revenue-report"),
    # Payouts
    path("payouts/", views.OwnerPayoutsView.as_view(), name="payouts-list"),
    path("payouts/<int:pk>/", views.OwnerPayoutDetailView.as_view(), name="payout-detail"),
    # Profile
    path("profile/", views.OwnerProfileView.as_view(), name="profile"),
]
