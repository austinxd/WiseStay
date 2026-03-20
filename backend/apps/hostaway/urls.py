from django.urls import path

from . import views

app_name = "hostaway"

urlpatterns = [
    # Webhook endpoint (public, auth via Basic Auth)
    path(
        "webhooks/unified/",
        views.HostawayWebhookView.as_view(),
        name="webhook-unified",
    ),
    # Manual sync triggers (admin only)
    path(
        "sync/listings/",
        views.ManualSyncListingsView.as_view(),
        name="sync-listings",
    ),
    path(
        "sync/reservations/",
        views.ManualSyncReservationsView.as_view(),
        name="sync-reservations",
    ),
    path(
        "sync/calendar/",
        views.ManualSyncCalendarView.as_view(),
        name="sync-calendar",
    ),
    # Sync logs (admin only)
    path(
        "sync/logs/",
        views.SyncLogListView.as_view(),
        name="sync-logs",
    ),
]
