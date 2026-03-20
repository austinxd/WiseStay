import { useQuery } from '@tanstack/react-query';
import { ownerService } from '@/services/ownerService';

export function useOwnerDashboard() {
  return useQuery({ queryKey: ['owner-dashboard'], queryFn: ownerService.getDashboard });
}

export function useOwnerProperties() {
  return useQuery({ queryKey: ['owner-properties'], queryFn: ownerService.getProperties });
}

export function usePropertyPerformance(id: number, period?: string) {
  return useQuery({ queryKey: ['property-performance', id, period], queryFn: () => ownerService.getPerformance(id, period), enabled: !!id });
}

export function useOccupancyCalendar(id: number, month: number, year: number) {
  return useQuery({ queryKey: ['occupancy', id, month, year], queryFn: () => ownerService.getOccupancy(id, month, year), enabled: !!id });
}
