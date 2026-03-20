import logging
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.utils.text import slugify

logger = logging.getLogger(__name__)

# Hostaway propertyTypeId → WiseStay property_type
PROPERTY_TYPE_MAP = {
    1: "house",
    2: "apartment",
    3: "condo",
    4: "villa",
    5: "cabin",
    6: "townhouse",
}

# Hostaway channelId → WiseStay channel
CHANNEL_MAP = {
    2000: "airbnb",
    2002: "booking",
    2003: "vrbo",
    2005: "direct",
}

# Hostaway status → WiseStay Reservation status
RESERVATION_STATUS_MAP = {
    "new": "confirmed",
    "modified": "confirmed",
    "confirmed": "confirmed",
    "ownerApproved": "confirmed",
    "cancelled": "cancelled",
    "declined": "cancelled",
    "closed": "checked_out",
}

# Known Hostaway amenity → WiseStay category mapping
AMENITY_CATEGORY_MAP = {
    "wifi": "essentials",
    "internet": "essentials",
    "tv": "entertainment",
    "cable tv": "entertainment",
    "air conditioning": "essentials",
    "heating": "essentials",
    "washer": "essentials",
    "dryer": "essentials",
    "kitchen": "kitchen",
    "cooking basics": "kitchen",
    "dishes and silverware": "kitchen",
    "refrigerator": "kitchen",
    "microwave": "kitchen",
    "oven": "kitchen",
    "stove": "kitchen",
    "dishwasher": "kitchen",
    "coffee maker": "kitchen",
    "pool": "outdoor",
    "hot tub": "outdoor",
    "patio or balcony": "outdoor",
    "garden or backyard": "outdoor",
    "bbq grill": "outdoor",
    "outdoor furniture": "outdoor",
    "free parking on premises": "parking",
    "garage": "parking",
    "ev charger": "parking",
    "fire extinguisher": "safety",
    "smoke alarm": "safety",
    "carbon monoxide alarm": "safety",
    "first aid kit": "safety",
    "wheelchair accessible": "accessibility",
    "elevator": "accessibility",
}


def _safe_decimal(value, default="0.00") -> Decimal:
    """Safely convert a value to Decimal."""
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        logger.warning("Could not convert %r to Decimal, using default %s", value, default)
        return Decimal(default)


def _parse_time(value, default=None) -> time | None:
    """Parse HH:MM or HH:MM:SS string to time object."""
    if not value:
        return default
    if isinstance(value, time):
        return value
    try:
        parts = str(value).split(":")
        return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        logger.warning("Could not parse time %r, using default", value)
        return default


def _parse_date(value) -> date | None:
    """Parse YYYY-MM-DD string to date object."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("Could not parse date %r", value)
        return None


def _generate_unique_slug(name: str, existing_slugs: set = None) -> str:
    """Generate a slug, appending a counter if needed to avoid duplicates."""
    base_slug = slugify(name)[:200] or "property"
    if existing_slugs is None:
        return base_slug
    slug = base_slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def map_listing_to_property(hostaway_listing: dict, owner_id: int, existing_slugs: set = None) -> dict:
    """
    Transform a Hostaway listing JSON into a dict of Property model fields.
    """
    listing_id = hostaway_listing.get("id")
    if not listing_id:
        logger.error("Hostaway listing missing 'id' field")
        return {}

    name = (
        hostaway_listing.get("externalListingName")
        or hostaway_listing.get("name")
        or hostaway_listing.get("internalListingName")
        or f"Property {listing_id}"
    )

    property_type_id = hostaway_listing.get("propertyTypeId")
    property_type = PROPERTY_TYPE_MAP.get(property_type_id, "house")

    is_active = hostaway_listing.get("isActive")
    if is_active in (1, "1", True):
        status = "active"
    elif is_active in (0, "0", False):
        status = "inactive"
    else:
        status = "onboarding"

    base_rate = _safe_decimal(hostaway_listing.get("price"), "100.00")
    cleaning_fee = _safe_decimal(hostaway_listing.get("cleaningFee"))

    check_in_str = hostaway_listing.get("checkInTimeStart") or hostaway_listing.get("checkInTime")
    check_out_str = hostaway_listing.get("checkOutTime")

    return {
        "owner_id": owner_id,
        "hostaway_listing_id": str(listing_id),
        "name": name[:200],
        "slug": _generate_unique_slug(name, existing_slugs),
        "description": hostaway_listing.get("description", "") or "",
        "property_type": property_type,
        "status": status,
        "address": hostaway_listing.get("address") or hostaway_listing.get("street") or "",
        "city": (hostaway_listing.get("city") or "")[:100],
        "state": (hostaway_listing.get("state") or "")[:2],
        "zip_code": (hostaway_listing.get("zipcode") or hostaway_listing.get("zipCode") or "")[:10],
        "country": (hostaway_listing.get("countryCode") or hostaway_listing.get("country") or "US")[:2],
        "latitude": _safe_decimal(hostaway_listing.get("latitude"), "0") or None,
        "longitude": _safe_decimal(hostaway_listing.get("longitude"), "0") or None,
        "bedrooms": int(hostaway_listing.get("bedrooms") or 1),
        "bathrooms": _safe_decimal(hostaway_listing.get("bathrooms"), "1.0"),
        "max_guests": int(hostaway_listing.get("maxGuests") or hostaway_listing.get("personCapacity") or 2),
        "beds": int(hostaway_listing.get("beds") or 1),
        "base_nightly_rate": base_rate,
        "cleaning_fee": cleaning_fee,
        "currency": (hostaway_listing.get("currency") or "USD")[:3],
        "check_in_time": _parse_time(check_in_str, time(16, 0)),
        "check_out_time": _parse_time(check_out_str, time(11, 0)),
        "min_nights": int(hostaway_listing.get("minNights") or 1),
        "max_nights": int(hostaway_listing.get("maxNights") or 365),
        "meta_title": (hostaway_listing.get("seoTitle") or name)[:70],
        "meta_description": (hostaway_listing.get("seoDescription") or "")[:160],
        "hostaway_raw_data": hostaway_listing,
    }


def map_listing_images(hostaway_listing: dict) -> list[dict]:
    """Extract and map images array from a Hostaway listing."""
    images = hostaway_listing.get("images") or []
    result = []
    for i, img in enumerate(images):
        url = img.get("url") or img.get("originalUrl")
        if not url:
            continue
        result.append({
            "url": url[:500],
            "caption": (img.get("caption") or "")[:200],
            "sort_order": int(img.get("sortOrder") or i),
            "is_cover": i == 0,
            "hostaway_image_id": str(img.get("id", "")),
        })
    return result


def map_listing_amenities(hostaway_listing: dict) -> list[dict]:
    """Extract and categorize amenities from a Hostaway listing."""
    amenities = hostaway_listing.get("listingAmenities") or hostaway_listing.get("amenities") or []
    result = []
    seen = set()
    for item in amenities:
        if isinstance(item, dict):
            name = item.get("name") or ""
        elif isinstance(item, str):
            name = item
        else:
            continue

        name = name.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())

        category = AMENITY_CATEGORY_MAP.get(name.lower(), "essentials")
        result.append({
            "name": name[:100],
            "category": category,
            "icon_name": "",
        })
    return result


def map_reservation_to_model(hostaway_reservation: dict) -> dict:
    """
    Transform a Hostaway reservation JSON into a dict for the Reservation model.
    """
    res_id = hostaway_reservation.get("id")
    if not res_id:
        logger.error("Hostaway reservation missing 'id' field")
        return {}

    channel_id = hostaway_reservation.get("channelId")
    channel = CHANNEL_MAP.get(channel_id, "other")

    ha_status = hostaway_reservation.get("status", "")
    status = RESERVATION_STATUS_MAP.get(ha_status, "pending")

    arrival = _parse_date(hostaway_reservation.get("arrivalDate"))
    departure = _parse_date(hostaway_reservation.get("departureDate"))
    nights = 0
    if arrival and departure:
        nights = (departure - arrival).days
    if nights <= 0:
        nights = int(hostaway_reservation.get("nights") or 1)

    total_price = _safe_decimal(hostaway_reservation.get("totalPrice"))
    base_price = _safe_decimal(hostaway_reservation.get("basePrice"))
    cleaning_fee = _safe_decimal(hostaway_reservation.get("cleaningFee"))
    host_fee = _safe_decimal(hostaway_reservation.get("hostChannelFee"))
    guest_fee = _safe_decimal(hostaway_reservation.get("guestChannelFee"))

    # Nightly rate: prefer basePrice / nights; fall back to totalPrice / nights
    if base_price and nights:
        nightly_rate = base_price / nights
    elif total_price and nights:
        nightly_rate = total_price / nights
    else:
        nightly_rate = Decimal("0.00")

    guest_first = hostaway_reservation.get("guestFirstName") or ""
    guest_last = hostaway_reservation.get("guestLastName") or ""
    guest_name = hostaway_reservation.get("guestName") or f"{guest_first} {guest_last}".strip() or "Guest"

    confirmation_code = (
        hostaway_reservation.get("channelReservationId")
        or hostaway_reservation.get("confirmationCode")
        or str(res_id)
    )

    return {
        "hostaway_reservation_id": str(res_id),
        "channel": channel,
        "status": status,
        "confirmation_code": str(confirmation_code)[:50],
        "check_in_date": arrival,
        "check_out_date": departure,
        "nights": nights,
        "guests_count": int(hostaway_reservation.get("numberOfGuests") or hostaway_reservation.get("adults") or 1),
        "guest_name": guest_name[:200],
        "guest_email": (hostaway_reservation.get("guestEmail") or "")[:254],
        "guest_phone": (hostaway_reservation.get("guestPhone") or "")[:20],
        "nightly_rate": round(nightly_rate, 2),
        "cleaning_fee": cleaning_fee,
        "service_fee": host_fee + guest_fee,
        "total_amount": total_price,
        "currency": (hostaway_reservation.get("currency") or "USD")[:3],
        "guest_notes": hostaway_reservation.get("guestNote") or "",
        "internal_notes": hostaway_reservation.get("hostNote") or "",
        "hostaway_raw_data": hostaway_reservation,
    }


def map_calendar_to_blocks(calendar_days: list[dict], property_id: int) -> list[dict]:
    """
    Group consecutive unavailable days into CalendarBlock ranges.

    Input: list of {date, isAvailable, ...} from Hostaway calendar endpoint.
    Output: list of {property_id, start_date, end_date, block_type, reason}.
    """
    blocks = []
    current_start = None
    current_end = None

    for day in sorted(calendar_days, key=lambda d: d.get("date", "")):
        day_date = _parse_date(day.get("date"))
        if day_date is None:
            continue

        is_available = day.get("isAvailable")
        if is_available in (0, False, "0"):
            if current_start is None:
                current_start = day_date
            current_end = day_date
        else:
            # Day is available — close any open block
            if current_start is not None:
                blocks.append({
                    "property_id": property_id,
                    "start_date": current_start,
                    "end_date": current_end,
                    "block_type": "hostaway_sync",
                    "reason": "Synced from Hostaway calendar",
                })
                current_start = None
                current_end = None

    # Close trailing block
    if current_start is not None:
        blocks.append({
            "property_id": property_id,
            "start_date": current_start,
            "end_date": current_end,
            "block_type": "hostaway_sync",
            "reason": "Synced from Hostaway calendar",
        })

    return blocks
