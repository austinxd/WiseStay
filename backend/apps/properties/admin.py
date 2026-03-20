from django.contrib import admin

from .models import CalendarBlock, Property, PropertyAmenity, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


class PropertyAmenityInline(admin.TabularInline):
    model = PropertyAmenity
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "property_type", "status", "city", "state")
    list_filter = ("status", "property_type", "state")
    search_fields = ("name", "slug", "address", "city")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [PropertyImageInline, PropertyAmenityInline]


@admin.register(CalendarBlock)
class CalendarBlockAdmin(admin.ModelAdmin):
    list_display = ("property", "start_date", "end_date", "block_type")
    list_filter = ("block_type",)
    search_fields = ("property__name",)
