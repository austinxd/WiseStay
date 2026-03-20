import { useMutation, useQuery } from '@tanstack/react-query';
import { reservationService } from '@/services/reservationService';

export function useAvailability(propertyId: number, checkIn: string, checkOut: string) {
  return useQuery({
    queryKey: ['availability', propertyId, checkIn, checkOut],
    queryFn: () => reservationService.checkAvailability(propertyId, checkIn, checkOut),
    enabled: !!propertyId && !!checkIn && !!checkOut,
  });
}

export function useCalendar(propertyId: number, month: number, year: number) {
  return useQuery({
    queryKey: ['calendar', propertyId, month, year],
    queryFn: () => reservationService.getCalendar(propertyId, month, year),
    enabled: !!propertyId,
  });
}

export function useCalculatePrice() {
  return useMutation({ mutationFn: reservationService.calculatePrice });
}

export function useCreateBooking() {
  return useMutation({ mutationFn: reservationService.createBooking });
}
