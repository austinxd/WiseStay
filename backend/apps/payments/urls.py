from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("webhooks/stripe/", views.StripeWebhookView.as_view(), name="stripe-webhook"),
    path("payouts/", views.OwnerPayoutsView.as_view(), name="payouts-list"),
    path("payouts/<int:pk>/", views.PayoutDetailView.as_view(), name="payout-detail"),
    path("payouts/<int:pk>/approve/", views.AdminPayoutApproveView.as_view(), name="payout-approve"),
    path("stripe-connect/onboard/", views.StripeConnectOnboardView.as_view(), name="stripe-connect-onboard"),
]
