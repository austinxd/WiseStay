import api from '@/config/api';

export const paymentService = {
  onboardStripeConnect: (returnUrl: string, refreshUrl: string) =>
    api.post<{ onboarding_url: string }>('/payments/stripe-connect/onboard/', { return_url: returnUrl, refresh_url: refreshUrl }).then(r => r.data),
};
