import calendar
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.domotics.models import NoiseAlert, SmartDevice
from apps.payments.models import OwnerPayout
from apps.properties.models import CalendarBlock, Property
from apps.reservations.models import Reservation

logger = logging.getLogger(__name__)


class OwnerDashboardService:

    @staticmethod
    def _owner_property_ids(owner_user_id: int) -> list[int]:
        return list(
            Property.objects.filter(owner_id=owner_user_id).values_list("id", flat=True)
        )

    @staticmethod
    def get_dashboard_summary(owner_user_id: int) -> dict:
        now = timezone.now()
        today = now.date()
        year = today.year
        month = today.month

        prop_ids = OwnerDashboardService._owner_property_ids(owner_user_id)

        # Properties
        props = Property.objects.filter(owner_id=owner_user_id)
        properties_count = props.count()
        active_properties = props.filter(status="active").count()

        # Base reservation queryset (completed/active, this year)
        base_qs = Reservation.objects.filter(property_id__in=prop_ids)
        completed_qs = base_qs.filter(status="checked_out")

        # Revenue
        ytd_revenue = completed_qs.filter(
            checked_out_at__year=year,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        current_month_rev = completed_qs.filter(
            checked_out_at__year=year, checked_out_at__month=month,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_month_rev = completed_qs.filter(
            checked_out_at__year=prev_year, checked_out_at__month=prev_month,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        mom_change = 0.0
        if prev_month_rev > 0:
            mom_change = round(float((current_month_rev - prev_month_rev) / prev_month_rev * 100), 2)

        # Reservations counts
        total_res_ytd = base_qs.filter(
            check_in_date__year=year,
        ).exclude(status="cancelled").count()

        upcoming = base_qs.filter(
            status="confirmed", check_in_date__gte=today,
        ).count()

        active_guests = base_qs.filter(status="checked_in").count()

        # Occupancy (current month)
        days_in_month = calendar.monthrange(year, month)[1]
        days_in_prev = calendar.monthrange(prev_year, prev_month)[1]

        def _calc_occ(pid_list, y, m, total_days):
            nights = Reservation.objects.filter(
                property_id__in=pid_list,
                status__in=["confirmed", "checked_in", "checked_out"],
                check_in_date__lte=date(y, m, total_days),
                check_out_date__gte=date(y, m, 1),
            ).aggregate(n=Sum("nights"))["n"] or 0
            max_nights = total_days * len(pid_list) if pid_list else 1
            return round(min(nights / max_nights * 100, 100), 1) if max_nights else 0

        curr_occ = _calc_occ(prop_ids, year, month, days_in_month)
        prev_occ = _calc_occ(prop_ids, prev_year, prev_month, days_in_prev)

        # YTD occupancy
        ytd_days = (today - date(year, 1, 1)).days or 1
        ytd_nights = base_qs.filter(
            status__in=["confirmed", "checked_in", "checked_out"],
            check_in_date__year=year,
        ).aggregate(n=Sum("nights"))["n"] or 0
        ytd_occ = round(min(ytd_nights / (ytd_days * max(len(prop_ids), 1)) * 100, 100), 1)

        # Payouts
        last_payout = OwnerPayout.objects.filter(
            owner_id=owner_user_id, status="paid",
        ).order_by("-paid_at").first()

        pending_amount = OwnerPayout.objects.filter(
            owner_id=owner_user_id, status__in=["draft", "approved"],
        ).aggregate(total=Sum("net_amount"))["total"] or Decimal("0")

        # Channel breakdown
        channel_data = (
            completed_qs.filter(checked_out_at__year=year)
            .values("channel")
            .annotate(count=Count("id"), revenue=Sum("total_amount"))
        )
        channel_breakdown = {}
        for row in channel_data:
            channel_breakdown[row["channel"]] = {
                "count": row["count"],
                "revenue": float(row["revenue"] or 0),
            }

        # Alerts
        alerts = []
        offline_devices = SmartDevice.objects.filter(
            property_id__in=prop_ids,
        ).exclude(status="online").exclude(status="setup")
        for d in offline_devices[:5]:
            alerts.append({
                "type": "device_offline",
                "message": f"{d.display_name} at {d.property.name} is {d.status}",
                "device_id": d.id,
            })

        low_battery = SmartDevice.objects.filter(
            property_id__in=prop_ids, status="online",
            battery_level__isnull=False, battery_level__lt=20,
        ).select_related("property")
        for d in low_battery[:5]:
            alerts.append({
                "type": "low_battery",
                "message": f"{d.display_name} at {d.property.name} battery at {d.battery_level}%",
                "device_id": d.id,
            })

        noise_alerts = NoiseAlert.objects.filter(
            device__property_id__in=prop_ids,
            resolved_at__isnull=True,
        ).select_related("device__property").order_by("-created_at")[:5]
        for na in noise_alerts:
            alerts.append({
                "type": "noise_alert",
                "message": f"Noise alert at {na.device.property.name} ({na.decibel_level} dB)",
                "alert_id": na.id,
            })

        return {
            "properties_count": properties_count,
            "active_properties": active_properties,
            "total_reservations_ytd": total_res_ytd,
            "upcoming_reservations": upcoming,
            "active_guests_now": active_guests,
            "revenue": {
                "current_month": float(current_month_rev),
                "previous_month": float(prev_month_rev),
                "ytd": float(ytd_revenue),
                "month_over_month_change": mom_change,
            },
            "occupancy": {
                "current_month_percent": curr_occ,
                "previous_month_percent": prev_occ,
                "ytd_percent": ytd_occ,
            },
            "payouts": {
                "last_payout_amount": float(last_payout.net_amount) if last_payout else 0,
                "last_payout_date": last_payout.paid_at.date().isoformat() if last_payout and last_payout.paid_at else None,
                "pending_amount": float(pending_amount),
                "next_payout_date": date(year, month + 1 if month < 12 else 1, 5).isoformat() if month < 12 else date(year + 1, 1, 5).isoformat(),
            },
            "channel_breakdown_ytd": channel_breakdown,
            "alerts": alerts,
        }

    @staticmethod
    def get_property_performance(property_id: int, owner_user_id: int, period: str = "ytd") -> dict:
        prop = Property.objects.get(pk=property_id, owner_id=owner_user_id)

        today = date.today()
        year = today.year

        if period == "month":
            start = today.replace(day=1)
            end = today
        elif period == "quarter":
            q_month = ((today.month - 1) // 3) * 3 + 1
            start = date(year, q_month, 1)
            end = today
        elif period == "year":
            start = date(year, 1, 1)
            end = date(year, 12, 31)
        elif period == "all":
            start = date(2020, 1, 1)
            end = today
        else:  # ytd
            start = date(year, 1, 1)
            end = today

        res_qs = Reservation.objects.filter(
            property=prop,
            check_in_date__gte=start,
            check_in_date__lte=end,
        ).exclude(status="cancelled")

        completed = res_qs.filter(status="checked_out")

        # Revenue by month
        from django.db.models.functions import TruncMonth
        rev_by_month = (
            completed.annotate(m=TruncMonth("checked_out_at"))
            .values("m")
            .annotate(revenue=Sum("total_amount"), count=Count("id"))
            .order_by("m")
        )

        total_revenue = completed.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        commission_rate = prop.owner.owner_profile.commission_rate
        commission = (total_revenue * commission_rate).quantize(Decimal("0.01"))
        net = total_revenue - commission

        avg_nightly = completed.aggregate(a=Sum("nightly_rate"))
        total_nights = completed.aggregate(n=Sum("nights"))["n"] or 0
        avg_rate = float(total_revenue / total_nights) if total_nights else 0

        # Occupancy by month
        occ_by_month = []
        for entry in rev_by_month:
            m = entry["m"]
            if m:
                month_days = calendar.monthrange(m.year, m.month)[1]
                month_nights = res_qs.filter(
                    check_in_date__month=m.month, check_in_date__year=m.year,
                ).aggregate(n=Sum("nights"))["n"] or 0
                occ_by_month.append({
                    "month": m.strftime("%Y-%m"),
                    "percent": round(min(month_nights / month_days * 100, 100), 1),
                    "nights_booked": month_nights,
                })

        # Reservation stats
        by_channel = dict(res_qs.values_list("channel").annotate(c=Count("id")).values_list("channel", "c"))
        by_status = dict(res_qs.values_list("status").annotate(c=Count("id")).values_list("status", "c"))
        total_count = res_qs.count()
        avg_stay = float(res_qs.aggregate(a=Sum("nights"))["a"] or 0) / total_count if total_count else 0
        avg_guests = float(res_qs.aggregate(a=Sum("guests_count"))["a"] or 0) / total_count if total_count else 0

        # Devices
        devices = list(SmartDevice.objects.filter(property=prop).values(
            "id", "display_name", "device_type", "brand", "status", "battery_level",
        ))

        # Noise alerts
        noise = list(NoiseAlert.objects.filter(
            device__property=prop,
        ).order_by("-created_at")[:10].values(
            "id", "decibel_level", "severity", "created_at", "resolved_at",
        ))

        cover = prop.images.filter(is_cover=True).first()

        return {
            "property": {
                "id": prop.id, "name": prop.name, "city": prop.city,
                "status": prop.status,
                "cover_image_url": cover.url if cover else None,
            },
            "revenue": {
                "total": float(total_revenue),
                "commission": float(commission),
                "net_to_owner": float(net),
                "average_nightly_rate": round(avg_rate, 2),
                "by_month": [
                    {"month": e["m"].strftime("%Y-%m") if e["m"] else "", "revenue": float(e["revenue"] or 0), "reservations": e["count"]}
                    for e in rev_by_month
                ],
            },
            "occupancy": {
                "total_percent": round(min(total_nights / max((end - start).days, 1) * 100, 100), 1),
                "by_month": occ_by_month,
            },
            "reservations": {
                "total": total_count,
                "by_channel": by_channel,
                "by_status": by_status,
                "average_stay_nights": round(avg_stay, 1),
                "average_guests": round(avg_guests, 1),
            },
            "devices": devices,
            "recent_noise_alerts": noise,
        }

    @staticmethod
    def get_reservations_for_owner(owner_user_id: int, property_id: int = None,
                                    status: str = None, upcoming_only: bool = False) -> "QuerySet":
        prop_ids = OwnerDashboardService._owner_property_ids(owner_user_id)
        qs = Reservation.objects.filter(
            property_id__in=prop_ids,
        ).select_related("property").order_by("-check_in_date")

        if property_id:
            if property_id not in prop_ids:
                return Reservation.objects.none()
            qs = qs.filter(property_id=property_id)
        if status:
            qs = qs.filter(status=status)
        if upcoming_only:
            qs = qs.filter(check_in_date__gte=date.today(), status="confirmed")
        return qs

    @staticmethod
    def get_revenue_report(owner_user_id: int, year: int, month: int = None) -> dict:
        props = Property.objects.filter(owner_id=owner_user_id).select_related("owner__owner_profile")

        filters = Q(status="checked_out", checked_out_at__year=year)
        if month:
            filters &= Q(checked_out_at__month=month)

        period = f"{year}-{month:02d}" if month else str(year)
        property_data = []
        totals = {"gross_revenue": Decimal("0"), "total_commission": Decimal("0"), "total_net": Decimal("0"), "total_reservations": 0}

        for prop in props:
            res_qs = Reservation.objects.filter(property=prop).filter(filters)
            gross = res_qs.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
            count = res_qs.count()
            if gross == 0 and count == 0:
                continue

            rate = prop.owner.owner_profile.commission_rate
            commission = (gross * rate).quantize(Decimal("0.01"))
            net = gross - commission

            by_channel = {}
            for row in res_qs.values("channel").annotate(r=Sum("total_amount")):
                by_channel[row["channel"]] = float(row["r"] or 0)

            property_data.append({
                "property_id": prop.id,
                "property_name": prop.name,
                "gross_revenue": float(gross),
                "commission_rate": float(rate),
                "commission_amount": float(commission),
                "net_revenue": float(net),
                "reservations_count": count,
                "by_channel": by_channel,
            })

            totals["gross_revenue"] += gross
            totals["total_commission"] += commission
            totals["total_net"] += net
            totals["total_reservations"] += count

        return {
            "period": period,
            "properties": property_data,
            "totals": {k: float(v) if isinstance(v, Decimal) else v for k, v in totals.items()},
        }

    @staticmethod
    def get_occupancy_calendar(property_id: int, owner_user_id: int, month: int, year: int) -> list[dict]:
        prop = Property.objects.get(pk=property_id, owner_id=owner_user_id)

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        reservations = Reservation.objects.filter(
            property=prop,
            status__in=["confirmed", "checked_in", "checked_out"],
            check_in_date__lte=last_day,
            check_out_date__gte=first_day,
        ).values("check_in_date", "check_out_date", "guest_name", "confirmation_code", "channel")

        blocks = CalendarBlock.objects.filter(
            property=prop,
            start_date__lte=last_day,
            end_date__gte=first_day,
        ).values("start_date", "end_date", "block_type", "reason")

        # Build date-keyed lookups
        booked_map = {}
        for r in reservations:
            d = max(r["check_in_date"], first_day)
            end = min(r["check_out_date"], last_day + timedelta(days=1))
            while d < end:
                booked_map[d] = r
                d += timedelta(days=1)

        blocked_map = {}
        for b in blocks:
            d = max(b["start_date"], first_day)
            end = min(b["end_date"], last_day)
            while d <= end:
                if d not in booked_map:
                    blocked_map[d] = b
                d += timedelta(days=1)

        result = []
        d = first_day
        while d <= last_day:
            if d in booked_map:
                r = booked_map[d]
                name = r["guest_name"]
                if " " in name:
                    parts = name.split()
                    name = f"{parts[0]} {parts[-1][0]}."
                result.append({
                    "date": d.isoformat(),
                    "status": "booked",
                    "guest_name": name,
                    "confirmation_code": r["confirmation_code"],
                    "channel": r["channel"],
                })
            elif d in blocked_map:
                b = blocked_map[d]
                result.append({
                    "date": d.isoformat(),
                    "status": "blocked",
                    "reason": b.get("reason") or b.get("block_type", ""),
                })
            else:
                result.append({"date": d.isoformat(), "status": "available"})
            d += timedelta(days=1)

        return result
