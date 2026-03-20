from django.db import migrations


def seed_tiers(apps, schema_editor):
    TierConfig = apps.get_model("loyalty", "TierConfig")
    tiers = [
        {
            "tier_name": "bronze",
            "min_reservations": 0,
            "min_referrals": 0,
            "discount_percent": 0,
            "early_checkin": False,
            "late_checkout": False,
            "priority_support": False,
            "bonus_points_on_upgrade": 0,
            "sort_order": 1,
            "is_active": True,
        },
        {
            "tier_name": "silver",
            "min_reservations": 3,
            "min_referrals": 1,
            "discount_percent": 5,
            "early_checkin": False,
            "late_checkout": False,
            "priority_support": False,
            "bonus_points_on_upgrade": 25,
            "sort_order": 2,
            "is_active": True,
        },
        {
            "tier_name": "gold",
            "min_reservations": 8,
            "min_referrals": 3,
            "discount_percent": 10,
            "early_checkin": True,
            "late_checkout": True,
            "priority_support": True,
            "bonus_points_on_upgrade": 50,
            "sort_order": 3,
            "is_active": True,
        },
        {
            "tier_name": "platinum",
            "min_reservations": 15,
            "min_referrals": 5,
            "discount_percent": 15,
            "early_checkin": True,
            "late_checkout": True,
            "priority_support": True,
            "bonus_points_on_upgrade": 100,
            "sort_order": 4,
            "is_active": True,
        },
    ]
    for tier in tiers:
        TierConfig.objects.get_or_create(tier_name=tier["tier_name"], defaults=tier)


def remove_tiers(apps, schema_editor):
    TierConfig = apps.get_model("loyalty", "TierConfig")
    TierConfig.objects.filter(
        tier_name__in=["bronze", "silver", "gold", "platinum"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tiers, remove_tiers),
    ]
