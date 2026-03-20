import logging

from apps.accounts.models import GuestProfile, User
from apps.reservations.models import Reservation

from .models import Conversation, Message

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_BASE = """You are WiseStay Concierge, a helpful and friendly AI assistant for WiseStay premium vacation rentals.

PERSONALITY:
- Warm, professional, and concise
- Respond in the same language the guest uses
- Never reveal you are an AI unless directly asked
- Use emojis sparingly and tastefully

RULES:
- NEVER invent information about properties — only use data from your context
- If unsure, use a tool to look up the answer rather than guessing
- For cancellations, refunds, or reservation modifications: ALWAYS escalate to a human agent
- Never discuss pricing from other platforms (Airbnb, Booking.com)
- Never share information about other guests
- Keep responses concise — 2-3 short paragraphs max

TOOLS:
You have access to tools to check availability, calculate prices, get access codes, look up loyalty info, get property details, and escalate to human support. Use them when needed."""


class ContextBuilder:

    @staticmethod
    def build_system_prompt(guest_user_id: int, reservation_id: int = None) -> str:
        parts = [SYSTEM_PROMPT_BASE]

        # Guest context
        try:
            user = User.objects.get(pk=guest_user_id)
            profile = GuestProfile.objects.get(user=user)
            parts.append(f"\n\nGUEST CONTEXT:\n- Name: {user.get_full_name() or user.email}\n- Email: {user.email}\n- Loyalty tier: {profile.loyalty_tier.title()}\n- Points balance: {profile.points_balance}\n- Direct bookings: {profile.direct_bookings_count}\n- Referral code: {profile.referral_code}")
        except (User.DoesNotExist, GuestProfile.DoesNotExist):
            pass

        # Reservation context
        if reservation_id:
            try:
                res = Reservation.objects.select_related("property").get(pk=reservation_id)
                prop = res.property
                parts.append(f"\n\nCURRENT RESERVATION:\n- Code: {res.confirmation_code}\n- Property: {prop.name}\n- Address: {prop.address}, {prop.city}, {prop.state}\n- Dates: {res.check_in_date} to {res.check_out_date} ({res.nights} nights)\n- Status: {res.status}\n- Guests: {res.guests_count}\n- Total: ${res.total_amount}\n- Check-in time: {prop.check_in_time.strftime('%I:%M %p')}\n- Check-out time: {prop.check_out_time.strftime('%I:%M %p')}")

                if res.discount_amount:
                    parts.append(f"- Discount applied: ${res.discount_amount}")
                if res.guest_notes:
                    parts.append(f"- Guest notes: {res.guest_notes}")

                # Property details
                amenities = list(prop.amenities.values_list("name", flat=True))
                if amenities:
                    parts.append(f"\nPROPERTY AMENITIES: {', '.join(amenities)}")

                raw = prop.hostaway_raw_data or {}
                if raw.get("houseRules"):
                    parts.append(f"\nHOUSE RULES: {raw['houseRules']}")
                if raw.get("specialInstruction"):
                    parts.append(f"\nSPECIAL INSTRUCTIONS: {raw['specialInstruction']}")
            except Reservation.DoesNotExist:
                pass

        return "\n".join(parts)

    @staticmethod
    def get_conversation_history(conversation_id: int, max_messages: int = 20) -> list[dict]:
        messages = (
            Message.objects.filter(conversation_id=conversation_id)
            .exclude(sender_type="system")
            .order_by("-created_at")[:max_messages]
        )
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            if msg.sender_type == "guest":
                history.append({"role": "user", "content": msg.content})
            elif msg.sender_type == "ai":
                entry = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    entry["tool_calls"] = msg.tool_calls
                history.append(entry)
            elif msg.sender_type == "human":
                history.append({"role": "assistant", "content": f"[Human agent]: {msg.content}"})

        return history
