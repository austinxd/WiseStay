import json
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from apps.hostaway.mappers import (
    map_calendar_to_blocks,
    map_listing_amenities,
    map_listing_images,
    map_listing_to_property,
    map_reservation_to_model,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict | list:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


class TestMapListingToProperty(TestCase):
    def setUp(self):
        self.listing = _load_fixture("listing.json")

    def test_basic_field_mapping(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["hostaway_listing_id"], "98765")
        self.assertEqual(result["name"], "Luxurious Malibu Beachfront Villa")
        self.assertEqual(result["property_type"], "villa")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["owner_id"], 1)

    def test_location_fields(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["city"], "Malibu")
        self.assertEqual(result["state"], "CA")
        self.assertEqual(result["zip_code"], "90265")
        self.assertEqual(result["country"], "US")
        self.assertAlmostEqual(float(result["latitude"]), 34.025922, places=4)

    def test_pricing_fields(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["base_nightly_rate"], Decimal("895.00"))
        self.assertEqual(result["cleaning_fee"], Decimal("250.00"))
        self.assertEqual(result["currency"], "USD")

    def test_capacity_fields(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["bedrooms"], 4)
        self.assertEqual(result["bathrooms"], Decimal("3.5"))
        self.assertEqual(result["beds"], 5)
        self.assertEqual(result["max_guests"], 10)

    def test_time_fields(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["check_in_time"], time(16, 0))
        self.assertEqual(result["check_out_time"], time(11, 0))

    def test_policy_fields(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["min_nights"], 2)
        self.assertEqual(result["max_nights"], 30)

    def test_slug_generation(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertIn("luxurious-malibu-beachfront-villa", result["slug"])

    def test_slug_dedup(self):
        existing = {"luxurious-malibu-beachfront-villa"}
        result = map_listing_to_property(self.listing, owner_id=1, existing_slugs=existing)
        self.assertEqual(result["slug"], "luxurious-malibu-beachfront-villa-1")

    def test_inactive_listing(self):
        self.listing["isActive"] = 0
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["status"], "inactive")

    def test_raw_data_preserved(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["hostaway_raw_data"]["id"], 98765)

    def test_missing_fields_dont_crash(self):
        minimal = {"id": 999, "name": "Minimal Listing"}
        result = map_listing_to_property(minimal, owner_id=1)
        self.assertEqual(result["hostaway_listing_id"], "999")
        self.assertEqual(result["property_type"], "house")  # default

    def test_missing_id_returns_empty(self):
        result = map_listing_to_property({}, owner_id=1)
        self.assertEqual(result, {})

    def test_seo_fields(self):
        result = map_listing_to_property(self.listing, owner_id=1)
        self.assertEqual(result["meta_title"], "Malibu Beachfront Villa | WiseStay")


class TestMapListingImages(TestCase):
    def setUp(self):
        self.listing = _load_fixture("listing.json")

    def test_images_mapped(self):
        images = map_listing_images(self.listing)
        self.assertEqual(len(images), 4)
        self.assertTrue(images[0]["is_cover"])
        self.assertFalse(images[1]["is_cover"])

    def test_image_fields(self):
        images = map_listing_images(self.listing)
        self.assertEqual(images[0]["url"], "https://img.hostaway.com/listings/98765/main-exterior.jpg")
        self.assertEqual(images[0]["caption"], "Beachfront exterior view")
        self.assertEqual(images[0]["hostaway_image_id"], "501")

    def test_empty_images(self):
        self.listing["images"] = []
        self.assertEqual(map_listing_images(self.listing), [])

    def test_missing_images_key(self):
        del self.listing["images"]
        self.assertEqual(map_listing_images(self.listing), [])


class TestMapListingAmenities(TestCase):
    def setUp(self):
        self.listing = _load_fixture("listing.json")

    def test_amenities_mapped(self):
        amenities = map_listing_amenities(self.listing)
        self.assertEqual(len(amenities), 15)

    def test_categories_assigned(self):
        amenities = map_listing_amenities(self.listing)
        by_name = {a["name"].lower(): a for a in amenities}
        self.assertEqual(by_name["wifi"]["category"], "essentials")
        self.assertEqual(by_name["pool"]["category"], "outdoor")
        self.assertEqual(by_name["kitchen"]["category"], "kitchen")
        self.assertEqual(by_name["tv"]["category"], "entertainment")
        self.assertEqual(by_name["free parking on premises"]["category"], "parking")
        self.assertEqual(by_name["smoke alarm"]["category"], "safety")

    def test_no_duplicates(self):
        self.listing["listingAmenities"].append({"name": "WiFi"})
        amenities = map_listing_amenities(self.listing)
        wifi_count = sum(1 for a in amenities if a["name"].lower() == "wifi")
        self.assertEqual(wifi_count, 1)


class TestMapReservationToModel(TestCase):
    def setUp(self):
        self.reservation = _load_fixture("reservation.json")

    def test_basic_mapping(self):
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["hostaway_reservation_id"], "54321")
        self.assertEqual(result["channel"], "airbnb")
        self.assertEqual(result["status"], "confirmed")

    def test_guest_fields(self):
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["guest_name"], "Sarah Johnson")
        self.assertEqual(result["guest_email"], "sarah.johnson@example.com")
        self.assertEqual(result["guest_phone"], "+14155559876")

    def test_date_fields(self):
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["check_in_date"], date(2025, 7, 15))
        self.assertEqual(result["check_out_date"], date(2025, 7, 20))
        self.assertEqual(result["nights"], 5)

    def test_financial_fields(self):
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["total_amount"], Decimal("5225.00"))
        self.assertEqual(result["cleaning_fee"], Decimal("250.00"))
        self.assertEqual(result["nightly_rate"], Decimal("895.00"))
        self.assertEqual(result["guests_count"], 4)

    def test_confirmation_code(self):
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["confirmation_code"], "HMAB12XYZ9")

    def test_channel_mapping_booking(self):
        self.reservation["channelId"] = 2002
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["channel"], "booking")

    def test_channel_mapping_vrbo(self):
        self.reservation["channelId"] = 2003
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["channel"], "vrbo")

    def test_channel_mapping_direct(self):
        self.reservation["channelId"] = 2005
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["channel"], "direct")

    def test_channel_mapping_unknown(self):
        self.reservation["channelId"] = 9999
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["channel"], "other")

    def test_status_mapping_cancelled(self):
        self.reservation["status"] = "cancelled"
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["status"], "cancelled")

    def test_status_mapping_closed(self):
        self.reservation["status"] = "closed"
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["status"], "checked_out")

    def test_notes_mapping(self):
        result = map_reservation_to_model(self.reservation)
        self.assertIn("birthday", result["guest_notes"])
        self.assertIn("VIP", result["internal_notes"])

    def test_raw_data_preserved(self):
        result = map_reservation_to_model(self.reservation)
        self.assertEqual(result["hostaway_raw_data"]["id"], 54321)

    def test_missing_id_returns_empty(self):
        result = map_reservation_to_model({})
        self.assertEqual(result, {})

    def test_missing_fields_defaults(self):
        minimal = {"id": 111, "arrivalDate": "2025-08-01", "departureDate": "2025-08-03"}
        result = map_reservation_to_model(minimal)
        self.assertEqual(result["guest_name"], "Guest")
        self.assertEqual(result["channel"], "other")
        self.assertEqual(result["nights"], 2)


class TestMapCalendarToBlocks(TestCase):
    def setUp(self):
        self.calendar = _load_fixture("calendar.json")

    def test_groups_consecutive_unavailable(self):
        blocks = map_calendar_to_blocks(self.calendar, property_id=1)
        # Days 12-19 (8 consecutive) and 23-24 (2 consecutive) are unavailable
        self.assertEqual(len(blocks), 2)

    def test_first_block_dates(self):
        blocks = map_calendar_to_blocks(self.calendar, property_id=1)
        self.assertEqual(blocks[0]["start_date"], date(2025, 7, 12))
        self.assertEqual(blocks[0]["end_date"], date(2025, 7, 19))
        self.assertEqual(blocks[0]["block_type"], "hostaway_sync")
        self.assertEqual(blocks[0]["property_id"], 1)

    def test_second_block_dates(self):
        blocks = map_calendar_to_blocks(self.calendar, property_id=1)
        self.assertEqual(blocks[1]["start_date"], date(2025, 7, 23))
        self.assertEqual(blocks[1]["end_date"], date(2025, 7, 24))

    def test_all_available(self):
        all_avail = [{"date": "2025-07-10", "isAvailable": 1}]
        blocks = map_calendar_to_blocks(all_avail, property_id=1)
        self.assertEqual(blocks, [])

    def test_all_unavailable(self):
        all_unavail = [
            {"date": "2025-07-10", "isAvailable": 0},
            {"date": "2025-07-11", "isAvailable": 0},
        ]
        blocks = map_calendar_to_blocks(all_unavail, property_id=1)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["start_date"], date(2025, 7, 10))
        self.assertEqual(blocks[0]["end_date"], date(2025, 7, 11))

    def test_empty_calendar(self):
        self.assertEqual(map_calendar_to_blocks([], property_id=1), [])
