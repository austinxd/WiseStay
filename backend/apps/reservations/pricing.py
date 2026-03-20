import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from apps.properties.models import Property

logger = logging.getLogger(__name__)

SERVICE_FEE_RATE = Decimal("0.10")  # 10% service fee to guest
DEFAULT_TAX_RATE = Decimal("0.00")  # TODO: per-jurisdiction tax calculation
MAX_DISCOUNT_FRACTION = Decimal("0.50")  # Combined discount cap


class PricingService:

    @staticmethod
    def calculate_price(property_id: int, check_in: date, check_out: date,
                        guest_user_id: int = None) -> dict:
        prop = Property.objects.get(pk=property_id)
        nights = (check_out - check_in).days
        if nights <= 0:
            raise ValueError("Check-out must be after check-in")

        nightly_rate = prop.base_nightly_rate
        subtotal = (nightly_rate * nights).quantize(Decimal("0.01"))
        cleaning_fee = prop.cleaning_fee
        service_fee = (subtotal * SERVICE_FEE_RATE).quantize(Decimal("0.01"))
        tax_rate = Decimal(str(prop.config.get("tax_rate", DEFAULT_TAX_RATE))) if isinstance(prop.hostaway_raw_data, dict) and "tax_rate" in prop.hostaway_raw_data else DEFAULT_TAX_RATE
        taxes = ((subtotal + cleaning_fee) * tax_rate).quantize(Decimal("0.01"))
        gross_total = subtotal + cleaning_fee + service_fee + taxes

        tier_discount = None
        loyalty = None
        total_before_points = gross_total

        if guest_user_id and prop.is_loyalty_eligible:
            try:
                from apps.loyalty.services import LoyaltyService
                disc_info = LoyaltyService.calculate_booking_discount(guest_user_id, subtotal)
                tier_discount_amount = Decimal(str(disc_info["tier_discount_amount"])).quantize(Decimal("0.01"))

                if tier_discount_amount > 0:
                    tier_discount = {
                        "tier_name": disc_info["tier_name"],
                        "percent": disc_info["tier_discount_percent"],
                        "amount": float(tier_discount_amount),
                    }
                    total_before_points = gross_total - tier_discount_amount

                loyalty = {
                    "points_available": disc_info["max_points_redeemable"] + (int(tier_discount_amount) if tier_discount_amount else 0),
                    "max_redeemable": disc_info["max_points_redeemable"],
                    "max_discount": disc_info["max_points_discount"],
                }
            except Exception:
                logger.debug("Loyalty calculation skipped", exc_info=True)

        max_total_discount = (gross_total * MAX_DISCOUNT_FRACTION).quantize(Decimal("0.01"))
        min_total = gross_total - max_total_discount

        return {
            "property_id": property_id,
            "nights": nights,
            "nightly_rate": float(nightly_rate),
            "subtotal": float(subtotal),
            "cleaning_fee": float(cleaning_fee),
            "service_fee": float(service_fee),
            "taxes": float(taxes),
            "gross_total": float(gross_total),
            "tier_discount": tier_discount,
            "loyalty": loyalty,
            "total_before_points": float(total_before_points),
            "min_total": float(min_total),
            "currency": prop.currency,
        }

    @staticmethod
    def calculate_final_amount(property_id: int, check_in: date, check_out: date,
                               guest_user_id: int, points_to_redeem: int = 0) -> dict:
        pricing = PricingService.calculate_price(property_id, check_in, check_out, guest_user_id)

        from apps.loyalty.constants import POINT_VALUE_USD

        points_discount = Decimal("0")
        if points_to_redeem > 0:
            points_discount = (Decimal(str(points_to_redeem)) * Decimal(str(POINT_VALUE_USD))).quantize(Decimal("0.01"))

        total_before_points = Decimal(str(pricing["total_before_points"]))
        min_total = Decimal(str(pricing["min_total"]))

        charge_amount = total_before_points - points_discount
        if charge_amount < min_total:
            charge_amount = min_total
            points_discount = total_before_points - min_total

        tier_discount_amount = Decimal(str(pricing["tier_discount"]["amount"])) if pricing["tier_discount"] else Decimal("0")
        total_discount = tier_discount_amount + points_discount

        pricing.update({
            "points_to_redeem": points_to_redeem,
            "points_discount": float(points_discount),
            "charge_amount": float(charge_amount),
            "total_discount": float(total_discount),
        })
        return pricing
