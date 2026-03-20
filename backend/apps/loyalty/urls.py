from django.urls import path

from . import views

app_name = "loyalty"

urlpatterns = [
    path("dashboard/", views.LoyaltyDashboardView.as_view(), name="dashboard"),
    path("points/history/", views.PointsHistoryView.as_view(), name="points-history"),
    path("points/redeem/", views.RedeemPointsView.as_view(), name="points-redeem"),
    path("calculate-discount/", views.CalculateDiscountView.as_view(), name="calculate-discount"),
    path("referrals/", views.ReferralInfoView.as_view(), name="referrals"),
    path("referrals/apply/", views.ApplyReferralCodeView.as_view(), name="referrals-apply"),
    path("tiers/", views.TierInfoView.as_view(), name="tiers"),
]
