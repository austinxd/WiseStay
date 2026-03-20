from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.loyalty.models import TierConfig
from apps.payments.models import OwnerPayout, PaymentRecord
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)


class TestStripeWebhookView(TestCase):
    def setUp(self):
        _seed_tiers()
        self.api = APIClient()
        self.url = "/api/v1/payments/webhooks/stripe/"
        owner = User.objects.create_user(username="o", email="o@t.com", password="t", role="owner")
        guest = User.objects.create_user(username="g", email="g@t.com", password="t", role="guest")
        prop = Property.objects.create(
            owner=owner, name="V", slug="v", property_type="villa",
            address="1", city="M", state="FL", zip_code="3",
            base_nightly_rate=Decimal("200"), status="active",
            is_direct_booking_enabled=True, min_nights=1,
        )
        self.res = Reservation.objects.create(
            property=prop, guest_user=guest, channel="direct", status="pending",
            confirmation_code="WS-WH0001",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=13),
            nights=3, guest_name="Test", nightly_rate=Decimal("200"),
            total_amount=Decimal("700"),
            stripe_payment_intent_id="pi_webhook_test",
        )
        PaymentRecord.objects.create(
            reservation=self.res, payment_type="charge", status="pending",
            amount=Decimal("700"), payment_intent_id="pi_webhook_test",
        )

    @patch("stripe.Webhook.construct_event")
    @patch("apps.hostaway.tasks.push_reservation_to_hostaway.delay")
    def test_payment_succeeded_confirms_booking(self, mock_push, mock_verify):
        mock_verify.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_webhook_test",
                    "metadata": {"reservation_id": str(self.res.id)},
                },
            },
        }

        response = self.api.post(
            self.url, b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=123,v1=abc",
        )

        self.assertEqual(response.status_code, 200)
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, "confirmed")

    @patch("stripe.Webhook.construct_event")
    def test_payment_failed_updates_record(self, mock_verify):
        mock_verify.return_value = {
            "type": "payment_intent.payment_failed",
            "data": {
                "object": {
                    "id": "pi_webhook_test",
                    "last_payment_error": {"message": "Card declined"},
                },
            },
        }

        response = self.api.post(
            self.url, b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=123,v1=abc",
        )

        self.assertEqual(response.status_code, 200)
        pr = PaymentRecord.objects.get(payment_intent_id="pi_webhook_test")
        self.assertEqual(pr.status, "failed")

    @patch("stripe.Webhook.construct_event", side_effect=Exception("Invalid signature"))
    def test_invalid_signature_rejected(self, mock_verify):
        response = self.api.post(
            self.url, b'{}', content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid",
        )
        self.assertEqual(response.status_code, 400)


class TestOwnerPayoutsView(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@t.com", password="t", role="owner",
        )
        OwnerPayout.objects.create(
            owner=self.owner, period_month=5, period_year=2025,
            gross_revenue=Decimal("5000"), commission_amount=Decimal("1000"),
            net_amount=Decimal("4000"), commission_rate_applied=Decimal("0.200"),
            status="paid",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_lists_payouts(self):
        response = self.api.get("/api/v1/payments/payouts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_guest_cannot_access(self):
        guest = User.objects.create_user(
            username="guest", email="g@t.com", password="t", role="guest",
        )
        self.api.force_authenticate(user=guest)
        response = self.api.get("/api/v1/payments/payouts/")
        self.assertEqual(response.status_code, 403)
