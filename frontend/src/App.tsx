import { Routes, Route } from 'react-router-dom';
import { PublicLayout } from '@/components/layout/PublicLayout';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { RoleGuard } from '@/components/auth/RoleRoute';

// Pages
import { HomePage } from '@/pages/HomePage';
import { PropertiesPage } from '@/pages/PropertiesPage';
import { PropertyDetailPage } from '@/pages/PropertyDetailPage';
import { LoyaltyProgramPage } from '@/pages/LoyaltyProgramPage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { TripsPage } from '@/pages/TripsPage';
import { TripDetailPage } from '@/pages/TripDetailPage';
import { LoyaltyPage } from '@/pages/LoyaltyPage';
import { ChatPage } from '@/pages/ChatPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { MyPropertiesPage } from '@/pages/MyPropertiesPage';
import { PropertyManagePage } from '@/pages/PropertyManagePage';
import { ReservationsPage } from '@/pages/ReservationsPage';
import { RevenuePage } from '@/pages/RevenuePage';
import { PayoutsPage } from '@/pages/PayoutsPage';
import { PayoutDetailPage } from '@/pages/PayoutDetailPage';
import { DevicesPage } from '@/pages/DevicesPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/properties" element={<PropertiesPage />} />
        <Route path="/properties/:slug" element={<PropertyDetailPage />} />
        <Route path="/loyalty-program" element={<LoyaltyProgramPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      {/* Authenticated routes — layout adapts by role */}
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:conversationId" element={<ChatPage />} />

        {/* Guest-only */}
        <Route path="/trips" element={<RoleGuard role="guest"><TripsPage /></RoleGuard>} />
        <Route path="/trips/:id" element={<RoleGuard role="guest"><TripDetailPage /></RoleGuard>} />
        <Route path="/loyalty" element={<RoleGuard role="guest"><LoyaltyPage /></RoleGuard>} />

        {/* Owner-only */}
        <Route path="/my-properties" element={<RoleGuard role="owner"><MyPropertiesPage /></RoleGuard>} />
        <Route path="/my-properties/:id" element={<RoleGuard role="owner"><PropertyManagePage /></RoleGuard>} />
        <Route path="/reservations" element={<RoleGuard role="owner"><ReservationsPage /></RoleGuard>} />
        <Route path="/revenue" element={<RoleGuard role="owner"><RevenuePage /></RoleGuard>} />
        <Route path="/payouts" element={<RoleGuard role="owner"><PayoutsPage /></RoleGuard>} />
        <Route path="/payouts/:id" element={<RoleGuard role="owner"><PayoutDetailPage /></RoleGuard>} />
        <Route path="/devices/:propertyId" element={<RoleGuard role="owner"><DevicesPage /></RoleGuard>} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
