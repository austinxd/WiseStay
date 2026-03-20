import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

CHATBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if a WiseStay property is available for specific dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer", "description": "The WiseStay property ID"},
                    "check_in": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                },
                "required": ["property_id", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_price",
            "description": "Calculate the price for a stay including loyalty discounts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["property_id", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_access_code",
            "description": "Get the guest's smart lock access code for their current reservation.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_loyalty_info",
            "description": "Get the guest's loyalty status, points, tier, and benefits.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_info",
            "description": "Get property details: amenities, house rules, check-in instructions, WiFi, parking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "integer",
                        "description": "Property ID. Uses current reservation property if omitted.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate to a human agent. Use for complaints, cancellations, refunds, safety issues, or when explicitly asked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Brief reason for escalation"},
                },
                "required": ["reason"],
            },
        },
    },
]


class ToolExecutor:
    """Executes GPT-4o function calls against WiseStay services."""

    def __init__(self, guest_user_id: int, reservation_id: int = None):
        self.guest_user_id = guest_user_id
        self.reservation_id = reservation_id

    def execute(self, function_name: str, arguments: dict) -> str:
        handler = getattr(self, function_name, None)
        if handler is None:
            return f"Unknown function: {function_name}"
        try:
            return handler(**arguments)
        except Exception as exc:
            logger.error("Tool %s failed: %s", function_name, exc, exc_info=True)
            return f"Sorry, I couldn't retrieve that information right now."

    def check_availability(self, property_id: int, check_in: str, check_out: str) -> str:
        from apps.reservations.availability import AvailabilityService

        ci = date.fromisoformat(check_in)
        co = date.fromisoformat(check_out)
        result = AvailabilityService.check_availability(property_id, ci, co)

        if result["available"]:
            return f"Property {property_id} is available from {check_in} to {check_out} ({result['nights']} nights)."
        return f"Property {property_id} is NOT available for those dates. Reason: {result.get('reason', 'unavailable')}."

    def calculate_price(self, property_id: int, check_in: str, check_out: str) -> str:
        from apps.reservations.pricing import PricingService

        ci = date.fromisoformat(check_in)
        co = date.fromisoformat(check_out)
        result = PricingService.calculate_price(property_id, ci, co, self.guest_user_id)

        lines = [
            f"Pricing for {result['nights']} nights:",
            f"- Nightly rate: ${result['nightly_rate']:.2f}/night",
            f"- Subtotal: ${result['subtotal']:.2f}",
            f"- Cleaning fee: ${result['cleaning_fee']:.2f}",
            f"- Service fee: ${result['service_fee']:.2f}",
        ]
        if result.get("taxes"):
            lines.append(f"- Taxes: ${result['taxes']:.2f}")
        lines.append(f"- Gross total: ${result['gross_total']:.2f}")

        if result.get("tier_discount"):
            td = result["tier_discount"]
            lines.append(f"- {td['tier_name'].title()} tier discount ({td['percent']}%): -${td['amount']:.2f}")
            lines.append(f"- Total after tier discount: ${result['total_before_points']:.2f}")

        if result.get("loyalty"):
            loy = result["loyalty"]
            if loy["max_redeemable"] > 0:
                lines.append(f"- Loyalty points available: {loy['max_redeemable']} (up to ${loy['max_discount']:.2f} off)")

        return "\n".join(lines)

    def get_access_code(self) -> str:
        if not self.reservation_id:
            return "No active reservation found. Your access code will be available 48 hours before check-in."

        from apps.domotics.models import LockAccessCode

        codes = LockAccessCode.objects.filter(
            reservation_id=self.reservation_id,
            status__in=["active", "scheduled"],
        ).select_related("device")

        if not codes.exists():
            return "No access code has been generated yet. It will be available 48 hours before your check-in."

        lines = []
        for code in codes:
            lines.append(
                f"Access code: {code.code} — {code.device.display_name}. "
                f"Valid from {code.valid_from.strftime('%b %d %I:%M %p')} "
                f"to {code.valid_until.strftime('%b %d %I:%M %p')}."
            )
        return "\n".join(lines)

    def get_loyalty_info(self) -> str:
        from apps.loyalty.services import LoyaltyService

        summary = LoyaltyService.get_guest_loyalty_summary(self.guest_user_id)

        lines = [
            f"Loyalty tier: {summary['tier'].title()}",
            f"Points balance: {summary['points_balance']}",
            f"Direct bookings: {summary['direct_bookings_count']}",
            f"Successful referrals: {summary['successful_referrals_count']}",
            f"Referral code: {summary['referral_code']}",
        ]

        benefits = summary.get("tier_benefits", {})
        if benefits:
            if benefits.get("discount_percent"):
                lines.append(f"Tier discount: {benefits['discount_percent']}% on direct bookings")
            if benefits.get("early_checkin"):
                lines.append("Benefit: Early check-in available")
            if benefits.get("late_checkout"):
                lines.append("Benefit: Late checkout available")
            if benefits.get("priority_support"):
                lines.append("Benefit: Priority support")

        next_tier = summary.get("next_tier")
        if next_tier:
            lines.append(
                f"Next tier ({next_tier['name'].title()}): "
                f"need {next_tier['reservations_needed']} more bookings "
                f"and {next_tier['referrals_needed']} more referrals"
            )

        if summary.get("points_expiring_soon"):
            exp = summary["points_expiring_soon"]
            lines.append(f"⚠ {exp['amount']} points expiring on {exp['expires_at'][:10]}")

        return "\n".join(lines)

    def get_property_info(self, property_id: int = None) -> str:
        from apps.properties.models import Property

        if property_id is None and self.reservation_id:
            from apps.reservations.models import Reservation
            try:
                res = Reservation.objects.get(pk=self.reservation_id)
                property_id = res.property_id
            except Reservation.DoesNotExist:
                pass

        if property_id is None:
            return "No property specified and no active reservation found."

        try:
            prop = Property.objects.get(pk=property_id)
        except Property.DoesNotExist:
            return f"Property {property_id} not found."

        lines = [
            f"Property: {prop.name}",
            f"Address: {prop.address}, {prop.city}, {prop.state} {prop.zip_code}",
            f"Type: {prop.property_type}",
            f"Bedrooms: {prop.bedrooms}, Bathrooms: {prop.bathrooms}, Max guests: {prop.max_guests}",
            f"Check-in: {prop.check_in_time.strftime('%I:%M %p')}, Check-out: {prop.check_out_time.strftime('%I:%M %p')}",
        ]

        amenities = list(prop.amenities.values_list("name", flat=True))
        if amenities:
            lines.append(f"Amenities: {', '.join(amenities)}")

        raw = prop.hostaway_raw_data or {}
        if raw.get("houseRules"):
            lines.append(f"House rules: {raw['houseRules']}")
        if raw.get("specialInstruction"):
            lines.append(f"Special instructions: {raw['specialInstruction']}")

        config = prop.hostaway_raw_data or {}
        wifi_name = config.get("wifiName") or config.get("wifi_name")
        wifi_pass = config.get("wifiPassword") or config.get("wifi_password")
        if wifi_name:
            lines.append(f"WiFi: {wifi_name}" + (f" / Password: {wifi_pass}" if wifi_pass else ""))

        return "\n".join(lines)

    def escalate_to_human(self, reason: str) -> str:
        from .models import Conversation, Message

        if self.reservation_id:
            convs = Conversation.objects.filter(
                guest_id=self.guest_user_id,
                reservation_id=self.reservation_id,
                status="active",
            )
        else:
            convs = Conversation.objects.filter(
                guest_id=self.guest_user_id,
                status="active",
            )

        for conv in convs:
            conv.status = "escalated"
            conv.save(update_fields=["status", "updated_at"])
            Message.objects.create(
                conversation=conv,
                sender_type="system",
                content=f"Escalated to human agent. Reason: {reason}",
            )

        return "I've connected you with our support team. A team member will be in touch shortly."
