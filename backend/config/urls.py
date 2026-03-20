from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/properties/", include("apps.properties.urls")),
    path("api/v1/hostaway/", include("apps.hostaway.urls")),
    path("api/v1/reservations/", include("apps.reservations.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/loyalty/", include("apps.loyalty.urls")),
    path("api/v1/domotics/", include("apps.domotics.urls")),
    path("api/v1/chatbot/", include("apps.chatbot.urls")),
    path("api/v1/owners/", include("apps.owners.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
