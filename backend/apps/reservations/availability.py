import calendar
import logging
from datetime import date, timedelta

from apps.properties.models import CalendarBlock, Property

from .models import Reservation

logger = logging.getLogger(__name__)

# Pending reservations block availability for this many minutes
PENDING_HOLD_MINUTES = 30


class AvailabilityService:

    @staticmethod
    def check_availability(property_id: int, check_in: date, check_out: date) -> dict:
        try:
            prop = Property.objects.get(pk=property_id)
        except Property.DoesNotExist:
            return {"available": False, "property_id": property_id, "check_in": str(check_in), "check_out": str(check_out), "nights": 0, "reason": "Property not found"}

        nights = (check_out - check_in).days
        base = {"property_id": property_id, "check_in": str(check_in), "check_out": str(check_out), "nights": nights}

        if prop.status != "active":
            return {**base, "available": False, "reason": "Property is not active"}
        if not prop.is_direct_booking_enabled:
            return {**base, "available": False, "reason": "Direct booking is not enabled for this property"}
        if nights <= 0:
            return {**base, "available": False, "reason": "Check-out must be after check-in"}
        if nights < prop.min_nights:
            return {**base, "available": False, "reason": f"Minimum stay is {prop.min_nights} nights"}
        if nights > prop.max_nights:
            return {**base, "available": False, "reason": f"Maximum stay is {prop.max_nights} nights"}
        if check_in < date.today():
            return {**base, "available": False, "reason": "Check-in date cannot be in the past"}

        # Check overlapping reservations (confirmed, checked_in, or recent pending)
        from django.utils import timezone
        pending_cutoff = timezone.now() - timedelta(minutes=PENDING_HOLD_MINUTES)

        overlapping_reservations = Reservation.objects.filter(
            property_id=property_id,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        ).filter(
            # Active reservations
            status__in=["confirmed", "checked_in"],
        ).exists()

        # Also check recent pending (within hold window)
        pending_overlap = Reservation.objects.filter(
            property_id=property_id,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
            status="pending",
            created_at__gte=pending_cutoff,
        ).exists()

        if overlapping_reservations or pending_overlap:
            return {**base, "available": False, "reason": "Property is not available for selected dates"}

        # Check calendar blocks
        block_overlap = CalendarBlock.objects.filter(
            property_id=property_id,
            start_date__lt=check_out,
            end_date__gt=check_in,
        ).exists()

        if block_overlap:
            return {**base, "available": False, "reason": "Property is not available for selected dates"}

        return {**base, "available": True, "reason": None}

    @staticmethod
    def get_available_dates(property_id: int, month: int, year: int) -> list[dict]:
        try:
            prop = Property.objects.get(pk=property_id)
        except Property.DoesNotExist:
            return []

        from django.utils import timezone

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Fetch all reservations and blocks for the month in one query each
        reservations = Reservation.objects.filter(
            property_id=property_id,
            check_in_date__lte=last_day,
            check_out_date__gte=first_day,
            status__in=["confirmed", "checked_in", "pending"],
        ).values_list("check_in_date", "check_out_date")

        blocks = CalendarBlock.objects.filter(
            property_id=property_id,
            start_date__lte=last_day,
            end_date__gte=first_day,
        ).values_list("start_date", "end_date")

        # Build set of unavailable dates
        unavailable = set()
        for ci, co in reservations:
            d = max(ci, first_day)
            end = min(co, last_day + timedelta(days=1))
            while d < end:
                unavailable.add(d)
                d += timedelta(days=1)
        for bs, be in blocks:
            d = max(bs, first_day)
            end = min(be, last_day + timedelta(days=1))
            while d <= end:
                unavailable.add(d)
                d += timedelta(days=1)

        result = []
        today = date.today()
        d = first_day
        while d <= last_day:
            if d < today or d in unavailable or prop.status != "active":
                result.append({"date": d.isoformat(), "available": False, "price": float(prop.base_nightly_rate), "min_stay": prop.min_nights})
            else:
                result.append({"date": d.isoformat(), "available": True, "price": float(prop.base_nightly_rate), "min_stay": prop.min_nights})
            d += timedelta(days=1)

        return result
