import { useQuery } from '@tanstack/react-query';
import { ownerService } from '@/services/ownerService';

export function useOwnerPayouts() {
  return useQuery({ queryKey: ['owner-payouts'], queryFn: ownerService.getPayouts });
}

export function useOwnerPayout(id: number) {
  return useQuery({ queryKey: ['owner-payout', id], queryFn: () => ownerService.getPayout(id), enabled: !!id });
}
