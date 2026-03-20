from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("book/", views.CreateBookingView.as_view(), name="book"),
    path("availability/", views.CheckAvailabilityView.as_view(), name="availability"),
    path("calendar/<int:property_id>/", views.CalendarAvailabilityView.as_view(), name="calendar"),
    path("calculate-price/", views.PriceCalculationView.as_view(), name="calculate-price"),
    path("my/", views.GuestReservationsView.as_view(), name="my-reservations"),
    path("<int:pk>/", views.ReservationDetailView.as_view(), name="detail"),
    path("<int:pk>/cancel/", views.CancelBookingView.as_view(), name="cancel"),
]
