import api from '@/config/api';
import type { AvailabilityResult, BookingResult, CalendarDay, PriceCalculation, Reservation } from '@/types/reservation';

interface PaginatedResponse<T> { count: number; next: string | null; previous: string | null; results: T[] }

export const reservationService = {
  checkAvailability: (propertyId: number, checkIn: string, checkOut: string) =>
    api.get<AvailabilityResult>('/reservations/availability/', { params: { property_id: propertyId, check_in: checkIn, check_out: checkOut } }).then(r => r.data),
  getCalendar: (propertyId: number, month: number, year: number) =>
    api.get<CalendarDay[]>(`/reservations/calendar/${propertyId}/`, { params: { month, year } }).then(r => r.data),
  calculatePrice: (data: { property_id: number; check_in: string; check_out: string; points_to_redeem?: number }) =>
    api.post<PriceCalculation>('/reservations/calculate-price/', data).then(r => r.data),
  createBooking: (data: { property_id: number; check_in: string; check_out: string; guests_count: number; points_to_redeem?: number; guest_notes?: string }) =>
    api.post<BookingResult>('/reservations/book/', data).then(r => r.data),
  getMyReservations: (params?: { status?: string; upcoming?: string; past?: string }) =>
    api.get<PaginatedResponse<Reservation>>('/reservations/my/', { params }).then(r => r.data),
  getReservation: (id: number) => api.get<Reservation>(`/reservations/${id}/`).then(r => r.data),
  cancelReservation: (id: number, reason?: string) => api.post(`/reservations/${id}/cancel/`, { reason }).then(r => r.data),
};
