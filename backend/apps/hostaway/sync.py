from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.properties.models import (
    CalendarBlock,
    Property,
    PropertyAmenity,
    PropertyImage,
)
from apps.reservations.models import Reservation

from .client import HostawayAPIClient
from .exceptions import HostawayAPIError
from .mappers import (
    map_calendar_to_blocks,
    map_listing_amenities,
    map_listing_images,
    map_listing_to_property,
    map_reservation_to_model,
)
from .models import SyncLog
from .signals import (
    reservation_cancelled,
    reservation_confirmed,
    reservation_dates_changed,
)

logger = logging.getLogger(__name__)

# Fields on Reservation that belong to WiseStay and must NOT be overwritten by sync
WISESTAY_PROTECTED_FIELDS = {
    "discount_amount",
    "points_earned",
    "points_redeemed",
    "stripe_payment_intent_id",
    "service_fee",
}


class HostawaySyncEngine:
    """Orchestrates bidirectional sync between WiseStay and Hostaway."""

    def __init__(self, triggered_by: str = "celery"):
        self.client = HostawayAPIClient()
        self.triggered_by = triggered_by

    # ------------------------------------------------------------------
    # Listings sync
    # ------------------------------------------------------------------

    def sync_all_listings(self, owner_mapping: dict | None = None):
        """
        Sync ALL listings from Hostaway into Property models.

        Args:
            owner_mapping: {hostaway_listing_id_str: owner_user_id}
                           If None, uses the existing owner on the local Property.
                           New listings without a mapping are created with status='onboarding'.
        """
        sync_log = SyncLog.objects.create(
            sync_type="listings",
            status="started",
            triggered_by=self.triggered_by,
        )
        created = updated = failed = 0
        errors = []

        try:
            all_listings = self._paginate_listings()
            existing_slugs = set(Property.objects.values_list("slug", flat=True))

            for listing in all_listings:
                try:
                    self._sync_single_listing(listing, owner_mapping, existing_slugs)
                    listing_id = str(listing.get("id", ""))

                    if Property.objects.filter(hostaway_listing_id=listing_id).exists():
                        # Determine if this was a create or update by checking
                        # whether the property existed before this sync run
                        prop = Property.objects.get(hostaway_listing_id=listing_id)
                        if prop.hostaway_last_synced_at is None or (
                            prop.hostaway_last_synced_at
                            and prop.hostaway_last_synced_at < sync_log.started_at
                        ):
                            created += 1
                        else:
                            updated += 1
                    else:
                        updated += 1
                except Exception as exc:
                    failed += 1
                    lid = listing.get("id", "unknown")
                    logger.error("Failed to sync listing %s: %s", lid, exc, exc_info=True)
                    errors.append({"listing_id": lid, "error": str(exc)})

            total = len(all_listings)
            sync_log.status = "success" if not failed else ("partial" if created + updated > 0 else "failed")
            sync_log.items_processed = total
            sync_log.items_created = created
            sync_log.items_updated = updated
            sync_log.items_failed = failed
            if errors:
                sync_log.error_details = errors
            sync_log.completed_at = timezone.now()
            sync_log.save()

            logger.info(
                "Listings sync complete: %s processed, %s created, %s updated, %s failed",
                total, created, updated, failed,
            )
        except Exception as exc:
            sync_log.status = "failed"
            sync_log.error_message = str(exc)
            sync_log.completed_at = timezone.now()
            sync_log.save()
            logger.error("Listings sync failed: %s", exc, exc_info=True)
            raise

        return sync_log

    def _paginate_listings(self) -> list[dict]:
        """Fetch all listings via pagination."""
        all_items = []
        offset = 0
        limit = 100
        while True:
            results = self.client.get_listings(limit=limit, offset=offset)
            if not results:
                break
            if isinstance(results, list):
                all_items.extend(results)
                if len(results) < limit:
                    break
            else:
                # Single object returned
                all_items.append(results)
                break
            offset += limit
        return all_items

    @transaction.atomic
    def _sync_single_listing(self, listing: dict, owner_mapping: dict | None, existing_slugs: set):
        """Create or update a single Property from a Hostaway listing."""
        listing_id = str(listing.get("id"))

        # Determine owner
        owner_id = None
        if owner_mapping:
            owner_id = owner_mapping.get(listing_id) or owner_mapping.get(int(listing_id))

        existing = Property.objects.filter(hostaway_listing_id=listing_id).first()

        if existing:
            owner_id = owner_id or existing.owner_id
        elif not owner_id:
            # New listing with no owner mapping — need a fallback
            admin_user = User.objects.filter(role="admin", is_active=True).first()
            if admin_user:
                owner_id = admin_user.id
                logger.warning(
                    "No owner mapping for listing %s, assigning to admin %s",
                    listing_id, admin_user.email,
                )
            else:
                logger.error("No owner mapping and no admin user for listing %s — skipping", listing_id)
                return

        prop_data = map_listing_to_property(listing, owner_id, existing_slugs)
        if not prop_data:
            return

        if existing:
            # Update — preserve slug if it exists, only update fields from Hostaway
            prop_data.pop("slug", None)
            for field, value in prop_data.items():
                if field not in ("hostaway_raw_data",):
                    setattr(existing, field, value)
            existing.hostaway_raw_data = listing
            existing.hostaway_last_synced_at = timezone.now()
            existing.save()
            prop = existing
        else:
            # Ensure slug is unique
            existing_slugs.add(prop_data["slug"])
            prop = Property.objects.create(
                **prop_data,
                hostaway_last_synced_at=timezone.now(),
            )

        # Sync images: delete and recreate (simpler than diffing)
        PropertyImage.objects.filter(property=prop).delete()
        images_data = map_listing_images(listing)
        for img_data in images_data:
            PropertyImage.objects.create(property=prop, **img_data)

        # Sync amenities: delete and recreate
        PropertyAmenity.objects.filter(property=prop).delete()
        amenities_data = map_listing_amenities(listing)
        for am_data in amenities_data:
            PropertyAmenity.objects.create(property=prop, **am_data)

    # ------------------------------------------------------------------
    # Reservations sync
    # ------------------------------------------------------------------

    def sync_reservations(self, modified_since: datetime | None = None):
        """
        Sync reservations modified since a given timestamp.
        If None, uses last successful reservations sync or last 90 days.
        """
        sync_log = SyncLog.objects.create(
            sync_type="reservations",
            status="started",
            triggered_by=self.triggered_by,
        )
        created = updated = failed = 0
        errors = []

        try:
            if modified_since is None:
                last_sync = (
                    SyncLog.objects.filter(
                        sync_type="reservations", status__in=["success", "partial"]
                    )
                    .exclude(pk=sync_log.pk)
                    .order_by("-started_at")
                    .first()
                )
                if last_sync:
                    modified_since = last_sync.started_at
                else:
                    modified_since = timezone.now() - timedelta(days=90)

            modified_since_str = modified_since.strftime("%Y-%m-%d %H:%M:%S")
            all_reservations = self._paginate_reservations(modified_since_str)

            for res_data in all_reservations:
                try:
                    was_created = self._sync_single_reservation(res_data)
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except Exception as exc:
                    failed += 1
                    rid = res_data.get("id", "unknown")
                    logger.error("Failed to sync reservation %s: %s", rid, exc, exc_info=True)
                    errors.append({"reservation_id": rid, "error": str(exc)})

            total = len(all_reservations)
            sync_log.status = "success" if not failed else ("partial" if created + updated > 0 else "failed")
            sync_log.items_processed = total
            sync_log.items_created = created
            sync_log.items_updated = updated
            sync_log.items_failed = failed
            if errors:
                sync_log.error_details = errors
            sync_log.completed_at = timezone.now()
            sync_log.save()

            logger.info(
                "Reservations sync complete: %s processed, %s created, %s updated, %s failed",
                total, created, updated, failed,
            )
        except Exception as exc:
            sync_log.status = "failed"
            sync_log.error_message = str(exc)
            sync_log.completed_at = timezone.now()
            sync_log.save()
            logger.error("Reservations sync failed: %s", exc, exc_info=True)
            raise

        return sync_log

    def _paginate_reservations(self, modified_since: str) -> list[dict]:
        all_items = []
        offset = 0
        limit = 100
        while True:
            results = self.client.get_reservations(
                modified_since=modified_since, limit=limit, offset=offset,
            )
            if not results:
                break
            if isinstance(results, list):
                all_items.extend(results)
                if len(results) < limit:
                    break
            else:
                all_items.append(results)
                break
            offset += limit
        return all_items

    @transaction.atomic
    def _sync_single_reservation(self, ha_reservation: dict) -> bool:
        """
        Create or update a single Reservation from Hostaway data.
        Returns True if created, False if updated.
        """
        ha_id = str(ha_reservation.get("id"))
        mapped = map_reservation_to_model(ha_reservation)
        if not mapped:
            raise ValueError(f"Mapper returned empty dict for reservation {ha_id}")

        # Resolve property
        listing_id = str(ha_reservation.get("listingMapId", ""))
        prop = Property.objects.filter(hostaway_listing_id=listing_id).first()
        if not prop:
            raise ValueError(
                f"No local property for Hostaway listing {listing_id} "
                f"(reservation {ha_id})"
            )
        mapped["property_id"] = prop.id

        # Try to match guest user by email
        guest_email = mapped.get("guest_email", "")
        if guest_email:
            guest_user = User.objects.filter(
                email__iexact=guest_email, role="guest", is_active=True
            ).first()
            if guest_user:
                mapped["guest_user_id"] = guest_user.id

        existing = Reservation.objects.filter(hostaway_reservation_id=ha_id).first()

        if existing:
            # --- UPDATE ---
            # Protect WiseStay-owned fields on direct bookings
            is_wisestay_direct = (
                existing.channel == "direct"
                and existing.stripe_payment_intent_id
            )

            old_check_in = existing.check_in_date
            old_check_out = existing.check_out_date
            old_status = existing.status

            for field, value in mapped.items():
                if field in ("hostaway_reservation_id", "confirmation_code"):
                    continue  # Never overwrite identifiers
                if is_wisestay_direct and field in WISESTAY_PROTECTED_FIELDS:
                    continue
                if is_wisestay_direct and field in (
                    "nightly_rate", "cleaning_fee", "total_amount", "taxes", "currency",
                ):
                    continue
                setattr(existing, field, value)

            existing.hostaway_raw_data = ha_reservation
            existing.save()

            # Fire signals for significant changes
            if old_status != existing.status:
                if existing.status == "cancelled":
                    reservation_cancelled.send(sender=Reservation, instance=existing)
                elif existing.status == "confirmed" and old_status == "pending":
                    reservation_confirmed.send(
                        sender=Reservation, instance=existing, created=False,
                    )

            if old_check_in != existing.check_in_date or old_check_out != existing.check_out_date:
                reservation_dates_changed.send(
                    sender=Reservation,
                    instance=existing,
                    old_check_in=old_check_in,
                    old_check_out=old_check_out,
                )

            return False  # updated

        else:
            # --- CREATE ---
            # Ensure confirmation_code is unique
            code = mapped.get("confirmation_code", ha_id)
            if Reservation.objects.filter(confirmation_code=code).exists():
                code = f"HA-{ha_id}"
                mapped["confirmation_code"] = code

            reservation = Reservation.objects.create(**mapped)

            if mapped.get("status") in ("confirmed", "checked_in"):
                reservation_confirmed.send(
                    sender=Reservation, instance=reservation, created=True,
                )

            return True  # created

    # ------------------------------------------------------------------
    # Calendar sync
    # ------------------------------------------------------------------

    def sync_calendar(self, property_id: int | None = None, months_ahead: int = 6):
        """
        Sync calendar availability from Hostaway.
        If property_id is given, sync only that property; otherwise sync all.
        """
        sync_log = SyncLog.objects.create(
            sync_type="calendar",
            status="started",
            triggered_by=self.triggered_by,
        )
        processed = created = failed = 0
        errors = []

        try:
            if property_id:
                properties = Property.objects.filter(pk=property_id, hostaway_listing_id__isnull=False)
            else:
                properties = Property.objects.filter(
                    hostaway_listing_id__isnull=False, status="active",
                )

            start = date.today()
            end = start + timedelta(days=months_ahead * 30)

            for prop in properties:
                try:
                    self._sync_property_calendar(prop, start, end)
                    processed += 1
                    # We count blocks created below, but for simplicity count properties
                except Exception as exc:
                    failed += 1
                    logger.error(
                        "Failed to sync calendar for property %s: %s",
                        prop.id, exc, exc_info=True,
                    )
                    errors.append({"property_id": prop.id, "error": str(exc)})

            sync_log.status = "success" if not failed else ("partial" if processed > 0 else "failed")
            sync_log.items_processed = processed + failed
            sync_log.items_created = processed  # properties synced
            sync_log.items_failed = failed
            if errors:
                sync_log.error_details = errors
            sync_log.completed_at = timezone.now()
            sync_log.save()

        except Exception as exc:
            sync_log.status = "failed"
            sync_log.error_message = str(exc)
            sync_log.completed_at = timezone.now()
            sync_log.save()
            raise

        return sync_log

    @transaction.atomic
    def _sync_property_calendar(self, prop: Property, start: date, end: date):
        """Sync calendar for a single property."""
        calendar_days = self.client.get_calendar(
            listing_id=int(prop.hostaway_listing_id),
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        )

        blocks = map_calendar_to_blocks(calendar_days or [], prop.id)

        # Remove old hostaway_sync blocks in this date range
        CalendarBlock.objects.filter(
            property=prop,
            block_type="hostaway_sync",
            start_date__gte=start,
            end_date__lte=end,
        ).delete()

        for block_data in blocks:
            CalendarBlock.objects.create(**block_data)

    # ------------------------------------------------------------------
    # Push direct reservation to Hostaway
    # ------------------------------------------------------------------

    def push_direct_reservation_to_hostaway(self, reservation_id: int) -> int:
        """
        Push a WiseStay direct reservation to Hostaway so it blocks
        the calendar on OTA channels.

        Returns the Hostaway reservation ID.
        """
        reservation = Reservation.objects.select_related("property", "guest_user").get(
            pk=reservation_id,
        )

        if reservation.channel != "direct":
            raise ValueError(f"Reservation {reservation_id} is not a direct booking (channel={reservation.channel})")
        if reservation.hostaway_reservation_id:
            logger.info("Reservation %s already has hostaway_id=%s", reservation_id, reservation.hostaway_reservation_id)
            return int(reservation.hostaway_reservation_id)

        prop = reservation.property
        if not prop.hostaway_listing_id:
            raise ValueError(f"Property {prop.id} has no hostaway_listing_id")

        guest_name = reservation.guest_name or "Guest"
        name_parts = guest_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        payload = {
            "listingMapId": int(prop.hostaway_listing_id),
            "channelId": 2005,
            "source": "WiseStay Direct",
            "guestName": guest_name,
            "guestFirstName": first_name,
            "guestLastName": last_name,
            "guestEmail": reservation.guest_email or "",
            "guestPhone": reservation.guest_phone or "",
            "arrivalDate": reservation.check_in_date.isoformat(),
            "departureDate": reservation.check_out_date.isoformat(),
            "numberOfGuests": reservation.guests_count,
            "totalPrice": float(reservation.total_amount),
            "currency": reservation.currency,
            "status": "confirmed",
            "isPaid": 1,
        }

        logger.info(
            "Pushing direct reservation %s to Hostaway (listing %s)",
            reservation_id, prop.hostaway_listing_id,
        )

        try:
            result = self.client.create_reservation(payload)
            ha_id = result.get("id") if isinstance(result, dict) else result
            reservation.hostaway_reservation_id = str(ha_id)
            reservation.save(update_fields=["hostaway_reservation_id", "updated_at"])
            logger.info("Reservation %s pushed to Hostaway as %s", reservation_id, ha_id)
            return int(ha_id)
        except HostawayAPIError:
            logger.critical(
                "Failed to push reservation %s to Hostaway — calendar may not be blocked on OTAs",
                reservation_id,
                exc_info=True,
            )
            raise
