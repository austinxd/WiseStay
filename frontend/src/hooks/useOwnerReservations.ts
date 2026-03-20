import { useQuery } from '@tanstack/react-query';
import { ownerService } from '@/services/ownerService';

export function useOwnerReservations(params?: { property_id?: number; status?: string; upcoming?: string }) {
  return useQuery({ queryKey: ['owner-reservations', params], queryFn: () => ownerService.getReservations(params) });
}

export function useOwnerReservation(id: number) {
  return useQuery({ queryKey: ['owner-reservation', id], queryFn: () => ownerService.getReservation(id), enabled: !!id });
}
