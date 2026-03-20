import api from '@/config/api';
import type { Property } from '@/types/property';

interface PropertyListParams {
  city?: string; check_in?: string; check_out?: string; guests?: number;
  min_price?: number; max_price?: number; bedrooms?: number; property_type?: string;
  page?: number;
}

interface PaginatedResponse<T> { count: number; next: string | null; previous: string | null; results: T[] }

export const propertyService = {
  list: (params?: PropertyListParams) => api.get<PaginatedResponse<Property>>('/properties/', { params }).then(r => r.data),
  get: (slug: string) => api.get<Property>(`/properties/${slug}/`).then(r => r.data),
};
