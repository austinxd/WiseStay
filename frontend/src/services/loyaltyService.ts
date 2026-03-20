import api from '@/config/api';
import type { LoyaltySummary, PointTransaction, ReferralStats, TierConfig } from '@/types/loyalty';

interface PaginatedResponse<T> { count: number; results: T[] }

export const loyaltyService = {
  getDashboard: () => api.get<LoyaltySummary>('/loyalty/dashboard/').then(r => r.data),
  getPointsHistory: (params?: { type?: string }) => api.get<PaginatedResponse<PointTransaction>>('/loyalty/points/history/', { params }).then(r => r.data),
  redeemPoints: (points: number, reservationId?: number) => api.post('/loyalty/points/redeem/', { points, reservation_id: reservationId }).then(r => r.data),
  calculateDiscount: (baseAmount: number) => api.post('/loyalty/calculate-discount/', { base_amount: baseAmount }).then(r => r.data),
  getReferralStats: () => api.get<ReferralStats>('/loyalty/referrals/').then(r => r.data),
  applyReferralCode: (code: string) => api.post('/loyalty/referrals/apply/', { referral_code: code }).then(r => r.data),
  getTiers: () => api.get<TierConfig[]>('/loyalty/tiers/').then(r => r.data),
};
