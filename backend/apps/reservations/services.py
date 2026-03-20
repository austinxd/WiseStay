import logging
import secrets
import string

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import GuestProfile, User
from apps.properties.models import Property

from .availability import AvailabilityService
from .models import Reservation
from .pricing import PricingService

logger = logging.getLogger(__name__)


class ReservationService:

    @staticmethod
    def generate_confirmation_code() -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "WS-" + "".join(secrets.choice(chars) for _ in range(6))
            if not Reservation.objects.filter(confirmation_code=code).exists():
                return code

    @staticmethod
    def initiate_direct_booking(
        guest_user_id: int,
        property_id: int,
        check_in: date,
        check_out: date,
        guests_count: int,
        points_to_redeem: int = 0,
        guest_notes: str = "",
    ) -> dict:
        # 1. Check availability
        avail = AvailabilityService.check_availability(property_id, check_in, check_out)
        if not avail["available"]:
            raise ValueError(avail["reason"])

        # 2. Calculate final pricing
        pricing = PricingService.calculate_final_amount(
            property_id, check_in, check_out, guest_user_id, points_to_redeem,
        )

        # 3. Validate points
        if points_to_redeem > 0:
            profile = GuestProfile.objects.get(user_id=guest_user_id)
            if profile.points_balance < points_to_redeem:
                raise ValueError(
                    f"Insufficient points: have {profile.points_balance}, need {points_to_redeem}"
                )

        user = User.objects.get(pk=guest_user_id)
        prop = Property.objects.get(pk=property_id)

        charge_amount = Decimal(str(pricing["charge_amount"]))
        nights = pricing["nights"]
        tier_discount_amount = Decimal(str(pricing["tier_discount"]["amount"])) if pricing["tier_discount"] else Decimal("0")
        points_discount = Decimal(str(pricing["points_discount"]))
        total_discount = tier_discount_amount + points_discount

        with transaction.atomic():
            # 4. Create reservation
            reservation = Reservation.objects.create(
                property=prop,
                guest_user=user,
                channel="direct",
                status="pending",
                confirmation_code=ReservationService.generate_confirmation_code(),
                check_in_date=check_in,
                check_out_date=check_out,
                nights=nights,
                guests_count=guests_count,
                guest_name=user.get_full_name() or user.email,
                guest_email=user.email,
                guest_phone=user.phone,
                nightly_rate=Decimal(str(pricing["nightly_rate"])),
                cleaning_fee=Decimal(str(pricing["cleaning_fee"])),
                service_fee=Decimal(str(pricing["service_fee"])),
                taxes=Decimal(str(pricing["taxes"])),
                total_amount=Decimal(str(pricing["total_before_points"])),
                discount_amount=total_discount,
                guest_notes=guest_notes,
            )

            # 5. Create Stripe PaymentIntent
            from apps.payments.stripe_service import StripeService

            amount_cents = int(charge_amount * 100)
            pi = StripeService.create_payment_intent(
                amount_cents=amount_cents,
                currency=prop.currency.lower(),
                metadata={
                    "reservation_id": str(reservation.id),
                    "confirmation_code": reservation.confirmation_code,
                    "property_name": prop.name,
                },
                receipt_email=user.email,
            )

            reservation.stripe_payment_intent_id = pi.id
            reservation.save(update_fields=["stripe_payment_intent_id", "updated_at"])

            # 6. Create PaymentRecord
            from apps.payments.models import PaymentRecord

            PaymentRecord.objects.create(
                reservation=reservation,
                payment_type="charge",
                status="pending",
                amount=charge_amount,
                currency=prop.currency,
                payment_intent_id=pi.id,
            )

        logger.info(
            "Initiated booking %s for property %s: charge=$%.2f",
            reservation.confirmation_code, prop.name, charge_amount,
        )

        return {
            "reservation_id": reservation.id,
            "confirmation_code": reservation.confirmation_code,
            "stripe_client_secret": pi.client_secret,
            "charge_amount": float(charge_amount),
            "breakdown": pricing,
        }

    @staticmethod
    def confirm_booking(reservation_id: int, stripe_payment_intent_id: str) -> Reservation:
        reservation = Reservation.objects.select_related("property", "guest_user").get(pk=reservation_id)

        if reservation.status == "confirmed":
            return reservation  # idempotent

        if reservation.status != "pending":
            raise ValueError(f"Cannot confirm reservation with status '{reservation.status}'")
        if reservation.stripe_payment_intent_id != stripe_payment_intent_id:
            raise ValueError("Payment intent ID mismatch")

        with transaction.atomic():
            reservation.status = "confirmed"
            reservation.confirmed_at = timezone.now()
            reservation.save(update_fields=["status", "confirmed_at", "updated_at"])

            # Update PaymentRecord
            from apps.payments.models import PaymentRecord

            PaymentRecord.objects.filter(
                reservation=reservation,
                payment_type="charge",
                status="pending",
            ).update(status="succeeded")

            # Redeem points if applicable
            if reservation.discount_amount > 0 and reservation.guest_user:
                tier_discount = Decimal("0")
                if reservation.guest_user and hasattr(reservation.guest_user, "guest_profile"):
                    try:
                        from apps.loyalty.services import LoyaltyService
                        disc = LoyaltyService.calculate_booking_discount(
                            reservation.guest_user_id,
                            reservation.nightly_rate * reservation.nights,
                        )
                        tier_discount = Decimal(str(disc.get("tier_discount_amount", 0)))
                    except Exception:
                        pass

                points_discount = reservation.discount_amount - tier_discount
                if points_discount > 0:
                    from apps.loyalty.constants import POINT_VALUE_USD
                    points_to_redeem = int(points_discount / Decimal(str(POINT_VALUE_USD)))
                    if points_to_redeem > 0:
                        try:
                            from apps.loyalty.services import LoyaltyService
                            LoyaltyService.redeem_points(
                                reservation.guest_user_id,
                                points_to_redeem,
                                reservation.id,
                            )
                        except Exception:
                            logger.warning("Failed to redeem points for reservation %s", reservation.id, exc_info=True)

        # Fire signals (outside transaction)
        from apps.hostaway.signals import reservation_confirmed
        reservation_confirmed.send(sender=Reservation, instance=reservation, created=True)

        # Push to Hostaway
        try:
            from apps.hostaway.tasks import push_reservation_to_hostaway
            push_reservation_to_hostaway.delay(reservation.id)
        except Exception:
            logger.warning("Failed to dispatch Hostaway push for %s", reservation.id, exc_info=True)

        logger.info("Booking confirmed: %s", reservation.confirmation_code)
        return reservation

    @staticmethod
    def cancel_booking(reservation_id: int, cancelled_by: str = "guest",
                       reason: str = "") -> Reservation:
        reservation = Reservation.objects.select_related("property", "guest_user").get(pk=reservation_id)

        if reservation.status in ("checked_in", "checked_out", "cancelled"):
            raise ValueError(f"Cannot cancel reservation with status '{reservation.status}'")

        with transaction.atomic():
            # Refund if payment was processed
            from apps.payments.models import PaymentRecord

            charge_record = PaymentRecord.objects.filter(
                reservation=reservation,
                payment_type="charge",
                status="succeeded",
            ).first()

            if charge_record:
                from apps.payments.stripe_service import StripeService

                amount_cents = int(charge_record.amount * 100)
                try:
                    refund = StripeService.create_refund(
                        payment_intent_id=reservation.stripe_payment_intent_id,
                        amount_cents=amount_cents,
                    )
                    PaymentRecord.objects.create(
                        reservation=reservation,
                        payment_type="refund",
                        status="succeeded",
                        amount=charge_record.amount,
                        currency=charge_record.currency,
                        refund_id=getattr(refund, "id", ""),
                        payment_intent_id=reservation.stripe_payment_intent_id,
                    )
                    charge_record.status = "refunded"
                    charge_record.save(update_fields=["status", "updated_at"])
                except Exception as exc:
                    logger.error("Refund failed for reservation %s: %s", reservation.id, exc)
                    PaymentRecord.objects.create(
                        reservation=reservation,
                        payment_type="refund",
                        status="failed",
                        amount=charge_record.amount,
                        currency=charge_record.currency,
                        failure_reason=str(exc),
                    )
            elif reservation.stripe_payment_intent_id:
                # Cancel unpaid PaymentIntent
                try:
                    from apps.payments.stripe_service import StripeService
                    StripeService.cancel_payment_intent(reservation.stripe_payment_intent_id)
                except Exception:
                    pass

            reservation.status = "cancelled"
            reservation.cancelled_at = timezone.now()
            reservation.internal_notes = f"{reservation.internal_notes}\nCancelled by {cancelled_by}: {reason}".strip()
            reservation.save(update_fields=["status", "cancelled_at", "internal_notes", "updated_at"])

        # Fire signal (outside transaction)
        from apps.hostaway.signals import reservation_cancelled
        reservation_cancelled.send(sender=Reservation, instance=reservation)

        logger.info("Booking cancelled: %s by %s", reservation.confirmation_code, cancelled_by)
        return reservation
