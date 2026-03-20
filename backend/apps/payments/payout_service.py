import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.reservations.models import Reservation

from .models import OwnerPayout, PayoutLineItem

logger = logging.getLogger(__name__)


class PayoutService:

    @staticmethod
    def generate_monthly_payouts(month: int, year: int) -> list[OwnerPayout]:
        reservations = Reservation.objects.filter(
            status="checked_out",
            checked_out_at__month=month,
            checked_out_at__year=year,
        ).select_related("property__owner__owner_profile")

        # Group by owner
        owner_reservations: dict[int, list] = {}
        for res in reservations:
            owner_id = res.property.owner_id
            owner_reservations.setdefault(owner_id, []).append(res)

        created_payouts = []

        for owner_id, res_list in owner_reservations.items():
            # Skip if payout already exists (idempotent)
            if OwnerPayout.objects.filter(
                owner_id=owner_id, period_month=month, period_year=year,
            ).exists():
                logger.info("Payout already exists for owner %s %s/%s", owner_id, month, year)
                continue

            owner = User.objects.select_related("owner_profile").get(pk=owner_id)
            commission_rate = owner.owner_profile.commission_rate

            gross_revenue = sum(r.total_amount for r in res_list)
            commission_amount = (gross_revenue * commission_rate).quantize(Decimal("0.01"))
            net_amount = gross_revenue - commission_amount

            with transaction.atomic():
                payout = OwnerPayout.objects.create(
                    owner=owner,
                    period_month=month,
                    period_year=year,
                    gross_revenue=gross_revenue,
                    commission_amount=commission_amount,
                    net_amount=net_amount,
                    commission_rate_applied=commission_rate,
                    status="draft",
                )

                for res in res_list:
                    res_commission = (res.total_amount * commission_rate).quantize(Decimal("0.01"))
                    PayoutLineItem.objects.create(
                        payout=payout,
                        reservation=res,
                        reservation_total=res.total_amount,
                        commission_amount=res_commission,
                        owner_amount=res.total_amount - res_commission,
                        guest_name=res.guest_name,
                        check_in_date=res.check_in_date,
                        check_out_date=res.check_out_date,
                        channel=res.channel,
                    )

            created_payouts.append(payout)
            logger.info(
                "Payout created for owner %s (%s/%s): gross=$%.2f, net=$%.2f",
                owner.email, month, year, gross_revenue, net_amount,
            )

        return created_payouts

    @staticmethod
    def approve_payout(payout_id: int, admin_user_id: int) -> OwnerPayout:
        payout = OwnerPayout.objects.get(pk=payout_id)
        if payout.status != "draft":
            raise ValueError(f"Cannot approve payout with status '{payout.status}'")

        payout.status = "approved"
        payout.approved_at = timezone.now()
        payout.admin_notes = f"Approved by admin user {admin_user_id}"
        payout.save(update_fields=["status", "approved_at", "admin_notes", "updated_at"])

        logger.info("Payout %s approved by admin %s", payout_id, admin_user_id)
        return payout

    @staticmethod
    def execute_approved_payouts() -> dict:
        from .stripe_service import StripeService

        payouts = OwnerPayout.objects.filter(status="approved").select_related(
            "owner__owner_profile",
        )

        paid = failed = skipped = 0

        for payout in payouts:
            profile = payout.owner.owner_profile
            if not profile.is_payout_enabled or not profile.stripe_account_id:
                payout.status = "failed"
                payout.admin_notes = "Stripe Connect not configured or payouts disabled"
                payout.save(update_fields=["status", "admin_notes", "updated_at"])
                skipped += 1
                continue

            amount_cents = int(payout.net_amount * 100)
            try:
                transfer = StripeService.create_transfer(
                    amount_cents=amount_cents,
                    destination_account_id=profile.stripe_account_id,
                    metadata={
                        "payout_id": str(payout.id),
                        "period": f"{payout.period_year}-{payout.period_month:02d}",
                        "owner_email": payout.owner.email,
                    },
                )
                payout.status = "paid"
                payout.paid_at = timezone.now()
                payout.stripe_transfer_id = transfer.id
                payout.save(update_fields=[
                    "status", "paid_at", "stripe_transfer_id", "updated_at",
                ])
                paid += 1
            except Exception as exc:
                payout.status = "failed"
                payout.admin_notes = f"Transfer failed: {exc}"
                payout.save(update_fields=["status", "admin_notes", "updated_at"])
                failed += 1
                logger.error("Payout %s transfer failed: %s", payout.id, exc)

        logger.info("Payouts executed: paid=%s, failed=%s, skipped=%s", paid, failed, skipped)
        return {"paid": paid, "failed": failed, "skipped": skipped}

    @staticmethod
    def get_owner_payout_summary(owner_user_id: int, year: int = None) -> dict:
        if year is None:
            year = timezone.now().year

        payouts = OwnerPayout.objects.filter(
            owner_id=owner_user_id,
            period_year=year,
        ).order_by("-period_month")

        total_revenue = payouts.aggregate(s=Sum("gross_revenue"))["s"] or Decimal("0")
        total_commission = payouts.aggregate(s=Sum("commission_amount"))["s"] or Decimal("0")
        total_paid = payouts.filter(status="paid").aggregate(s=Sum("net_amount"))["s"] or Decimal("0")
        pending = payouts.filter(status__in=["draft", "approved"]).aggregate(s=Sum("net_amount"))["s"] or Decimal("0")

        payout_list = []
        for p in payouts:
            payout_list.append({
                "id": p.id,
                "period": f"{p.period_year}-{p.period_month:02d}",
                "gross_revenue": float(p.gross_revenue),
                "commission": float(p.commission_amount),
                "net_amount": float(p.net_amount),
                "status": p.status,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "line_items_count": p.line_items.count(),
            })

        return {
            "total_revenue_ytd": float(total_revenue),
            "total_commission_ytd": float(total_commission),
            "total_paid_ytd": float(total_paid),
            "pending_payout": float(pending),
            "payouts": payout_list,
        }
