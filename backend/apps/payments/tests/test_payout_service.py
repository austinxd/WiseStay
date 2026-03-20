from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.payments.models import OwnerPayout, PayoutLineItem
from apps.payments.payout_service import PayoutService
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _setup():
    owner = User.objects.create_user(
        username="owner", email="owner@t.com", password="t", role="owner",
    )
    profile = owner.owner_profile
    profile.commission_rate = Decimal("0.200")
    profile.stripe_account_id = "acct_test_123"
    profile.is_payout_enabled = True
    profile.save()

    prop = Property.objects.create(
        owner=owner, name="Villa", slug="villa", property_type="villa",
        address="123 St", city="Miami", state="FL", zip_code="33139",
        base_nightly_rate=Decimal("200"),
    )
    return owner, prop


def _create_checked_out_reservation(prop, total, month=5, year=2025):
    return Reservation.objects.create(
        property=prop, channel="direct", status="checked_out",
        confirmation_code=f"WS-{Reservation.objects.count() + 1:06d}",
        check_in_date=date(year, month, 10),
        check_out_date=date(year, month, 15),
        nights=5, guest_name="Test", nightly_rate=Decimal("200"),
        total_amount=total,
        checked_out_at=timezone.now().replace(month=month, year=year),
    )


class TestGenerateMonthlyPayouts(TestCase):
    def setUp(self):
        self.owner, self.prop = _setup()

    def test_creates_payout_with_correct_amounts(self):
        _create_checked_out_reservation(self.prop, Decimal("1000"))
        _create_checked_out_reservation(self.prop, Decimal("500"))

        payouts = PayoutService.generate_monthly_payouts(5, 2025)

        self.assertEqual(len(payouts), 1)
        payout = payouts[0]
        self.assertEqual(payout.gross_revenue, Decimal("1500"))
        self.assertEqual(payout.commission_amount, Decimal("300"))  # 20%
        self.assertEqual(payout.net_amount, Decimal("1200"))
        self.assertEqual(payout.commission_rate_applied, Decimal("0.200"))
        self.assertEqual(payout.status, "draft")

    def test_creates_line_items(self):
        _create_checked_out_reservation(self.prop, Decimal("1000"))

        payouts = PayoutService.generate_monthly_payouts(5, 2025)
        items = PayoutLineItem.objects.filter(payout=payouts[0])
        self.assertEqual(items.count(), 1)
        self.assertEqual(items[0].reservation_total, Decimal("1000"))
        self.assertEqual(items[0].commission_amount, Decimal("200"))
        self.assertEqual(items[0].owner_amount, Decimal("800"))

    def test_idempotent(self):
        _create_checked_out_reservation(self.prop, Decimal("1000"))
        PayoutService.generate_monthly_payouts(5, 2025)
        payouts2 = PayoutService.generate_monthly_payouts(5, 2025)
        self.assertEqual(len(payouts2), 0)
        self.assertEqual(OwnerPayout.objects.count(), 1)

    def test_custom_commission_rate(self):
        self.owner.owner_profile.commission_rate = Decimal("0.150")
        self.owner.owner_profile.save()
        _create_checked_out_reservation(self.prop, Decimal("1000"))

        payouts = PayoutService.generate_monthly_payouts(5, 2025)
        self.assertEqual(payouts[0].commission_amount, Decimal("150"))
        self.assertEqual(payouts[0].net_amount, Decimal("850"))

    def test_no_reservations_no_payouts(self):
        payouts = PayoutService.generate_monthly_payouts(5, 2025)
        self.assertEqual(len(payouts), 0)


class TestApprovePayout(TestCase):
    def setUp(self):
        self.owner, self.prop = _setup()
        _create_checked_out_reservation(self.prop, Decimal("1000"))
        payouts = PayoutService.generate_monthly_payouts(5, 2025)
        self.payout = payouts[0]

    def test_approves_draft_payout(self):
        admin = User.objects.create_superuser(
            username="admin", email="admin@t.com", password="t",
        )
        result = PayoutService.approve_payout(self.payout.id, admin.id)
        self.assertEqual(result.status, "approved")
        self.assertIsNotNone(result.approved_at)

    def test_cannot_approve_non_draft(self):
        self.payout.status = "paid"
        self.payout.save()
        with self.assertRaises(ValueError):
            PayoutService.approve_payout(self.payout.id, 1)


class TestExecutePayouts(TestCase):
    def setUp(self):
        self.owner, self.prop = _setup()
        _create_checked_out_reservation(self.prop, Decimal("1000"))
        payouts = PayoutService.generate_monthly_payouts(5, 2025)
        self.payout = payouts[0]
        self.payout.status = "approved"
        self.payout.save()

    @patch("stripe.Transfer.create")
    def test_executes_transfer(self, mock_transfer_create):
        mock_transfer = MagicMock()
        mock_transfer.id = "tr_test_123"
        mock_transfer_create.return_value = mock_transfer

        result = PayoutService.execute_approved_payouts()

        self.assertEqual(result["paid"], 1)
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, "paid")
        self.assertEqual(self.payout.stripe_transfer_id, "tr_test_123")

    def test_skips_without_stripe_connect(self):
        self.owner.owner_profile.stripe_account_id = ""
        self.owner.owner_profile.save()

        result = PayoutService.execute_approved_payouts()
        self.assertEqual(result["skipped"], 1)
        self.payout.refresh_from_db()
        self.assertEqual(self.payout.status, "failed")


class TestOwnerPayoutSummary(TestCase):
    def setUp(self):
        self.owner, self.prop = _setup()

    def test_returns_summary(self):
        _create_checked_out_reservation(self.prop, Decimal("1000"))
        PayoutService.generate_monthly_payouts(5, 2025)

        summary = PayoutService.get_owner_payout_summary(self.owner.id, 2025)
        self.assertEqual(summary["total_revenue_ytd"], 1000.00)
        self.assertEqual(summary["total_commission_ytd"], 200.00)
        self.assertGreater(summary["pending_payout"], 0)
        self.assertEqual(len(summary["payouts"]), 1)
