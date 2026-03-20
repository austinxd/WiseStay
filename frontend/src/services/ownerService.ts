import api from '@/config/api';
import type { DashboardSummary, OccupancyDay, OwnerProfile, PropertyPerformance, RevenueReport } from '@/types/owner';
import type { OwnerPayout } from '@/types/payment';
import type { Reservation } from '@/types/reservation';
import type { PropertyListItem } from '@/types/property';
import type { SmartDevice } from '@/types/domotics';

interface PaginatedResponse<T> { count: number; results: T[] }

export const ownerService = {
  getDashboard: () => api.get<DashboardSummary>('/owners/dashboard/').then(r => r.data),
  getProperties: () => api.get<PaginatedResponse<PropertyListItem>>('/owners/properties/').then(r => r.data),
  getProperty: (id: number) => api.get(`/owners/properties/${id}/`).then(r => r.data),
  getPerformance: (id: number, period?: string) => api.get<PropertyPerformance>(`/owners/properties/${id}/performance/`, { params: { period } }).then(r => r.data),
  getOccupancy: (id: number, month: number, year: number) => api.get<OccupancyDay[]>(`/owners/properties/${id}/occupancy/`, { params: { month, year } }).then(r => r.data),
  getReservations: (params?: { property_id?: number; status?: string; upcoming?: string }) =>
    api.get<PaginatedResponse<Reservation>>('/owners/reservations/', { params }).then(r => r.data),
  getReservation: (id: number) => api.get<Reservation>(`/owners/reservations/${id}/`).then(r => r.data),
  getRevenue: (year: number, month?: number) => api.get<RevenueReport>('/owners/revenue/', { params: { year, month } }).then(r => r.data),
  getPayouts: () => api.get<PaginatedResponse<OwnerPayout>>('/owners/payouts/').then(r => r.data),
  getPayout: (id: number) => api.get<OwnerPayout>(`/owners/payouts/${id}/`).then(r => r.data),
  getDevices: (propertyId: number) => api.get<SmartDevice[]>(`/owners/properties/${propertyId}/devices/`).then(r => r.data),
  getProfile: () => api.get<OwnerProfile>('/owners/profile/').then(r => r.data),
  updateProfile: (data: { company_name: string }) => api.put<OwnerProfile>('/owners/profile/', data).then(r => r.data),
};
