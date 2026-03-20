import { useQuery } from '@tanstack/react-query';
import { loyaltyService } from '@/services/loyaltyService';

export function useLoyaltyDashboard() {
  return useQuery({ queryKey: ['loyalty-dashboard'], queryFn: loyaltyService.getDashboard });
}

export function usePointsHistory() {
  return useQuery({ queryKey: ['points-history'], queryFn: () => loyaltyService.getPointsHistory() });
}

export function useTiers() {
  return useQuery({ queryKey: ['tiers'], queryFn: loyaltyService.getTiers });
}

export function useReferralStats() {
  return useQuery({ queryKey: ['referral-stats'], queryFn: loyaltyService.getReferralStats });
}
