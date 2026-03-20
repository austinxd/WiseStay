export const ROUTES = {
  HOME: '/',
  PROPERTIES: '/properties',
  PROPERTY_DETAIL: '/properties/:slug',
  LOYALTY_PROGRAM: '/loyalty-program',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  CHAT: '/chat',
  CHAT_CONVERSATION: '/chat/:conversationId',
  // Guest
  TRIPS: '/trips',
  TRIP_DETAIL: '/trips/:id',
  LOYALTY: '/loyalty',
  // Owner
  MY_PROPERTIES: '/my-properties',
  PROPERTY_MANAGE: '/my-properties/:id',
  RESERVATIONS: '/reservations',
  REVENUE: '/revenue',
  PAYOUTS: '/payouts',
  PAYOUT_DETAIL: '/payouts/:id',
  DEVICES: '/devices/:propertyId',
} as const;
