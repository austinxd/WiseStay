import { useQuery } from '@tanstack/react-query';
import { reservationService } from '@/services/reservationService';

export function useMyReservations(params?: { status?: string; upcoming?: string }) {
  return useQuery({ queryKey: ['my-reservations', params], queryFn: () => reservationService.getMyReservations(params) });
}

export function useReservation(id: number) {
  return useQuery({ queryKey: ['reservation', id], queryFn: () => reservationService.getReservation(id), enabled: !!id });
}
