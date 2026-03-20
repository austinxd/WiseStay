import { useAuthStore } from '@/stores/authStore';
import { useOwnerDashboard } from '@/hooks/useOwnerDashboard';
import { useLoyaltyDashboard } from '@/hooks/useLoyalty';
import { useMyReservations } from '@/hooks/useReservations';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { Link } from 'react-router-dom';
import { TrendingUp, Users, Calendar, DollarSign, ArrowRight, Trophy } from 'lucide-react';

function GuestDashboard() {
  const { user } = useAuthStore();
  const { data: loyalty, isLoading: loyaltyLoading } = useLoyaltyDashboard();
  const { data: reservations } = useMyReservations({ upcoming: 'true' });
  if (loyaltyLoading) return <PageSpinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Welcome back, {user?.first_name || 'Guest'}!</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card><CardContent>
          <div className="flex items-center gap-3"><Trophy className="w-8 h-8 text-accent-500" /><div><p className="text-sm text-gray-500">Loyalty Tier</p><p className="text-xl font-bold capitalize">{loyalty?.tier || 'Bronze'}</p></div></div>
        </CardContent></Card>
        <Card><CardContent>
          <p className="text-sm text-gray-500">Points Balance</p><p className="text-2xl font-bold">{loyalty?.points_balance || 0}</p>
        </CardContent></Card>
        <Card><CardContent>
          <p className="text-sm text-gray-500">Upcoming Trips</p><p className="text-2xl font-bold">{reservations?.count || 0}</p>
        </CardContent></Card>
      </div>
      {reservations?.results?.[0] && (
        <Card><CardContent>
          <div className="flex items-center justify-between">
            <div><h3 className="font-semibold">Next Trip: {reservations.results[0].property_name}</h3><p className="text-sm text-gray-500">{reservations.results[0].check_in_date} to {reservations.results[0].check_out_date}</p></div>
            <Link to={`/trips/${reservations.results[0].id}`}><ArrowRight className="w-5 h-5 text-wisestay-600" /></Link>
          </div>
        </CardContent></Card>
      )}
      <div className="flex gap-4">
        <Link to="/properties"><Card className="flex-1 hover:shadow-md cursor-pointer"><CardContent className="text-center"><p className="font-medium text-wisestay-600">Browse Properties</p></CardContent></Card></Link>
        <Link to="/chat"><Card className="flex-1 hover:shadow-md cursor-pointer"><CardContent className="text-center"><p className="font-medium text-wisestay-600">Chat with Concierge</p></CardContent></Card></Link>
      </div>
    </div>
  );
}

function OwnerDashboard() {
  const { data, isLoading } = useOwnerDashboard();
  if (isLoading) return <PageSpinner />;
  if (!data) return null;
  const stats = [
    { label: 'Revenue MTD', value: `$${data.revenue.current_month.toLocaleString()}`, icon: DollarSign, change: `${data.revenue.month_over_month_change > 0 ? '+' : ''}${data.revenue.month_over_month_change}%` },
    { label: 'Occupancy', value: `${data.occupancy.current_month_percent}%`, icon: Calendar },
    { label: 'Active Guests', value: data.active_guests_now, icon: Users },
    { label: 'Upcoming', value: data.upcoming_reservations, icon: TrendingUp },
  ];
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Owner Dashboard</h1>
      {data.alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="font-medium text-red-800 mb-2">Alerts</p>
          {data.alerts.slice(0,3).map((a,i) => <p key={i} className="text-sm text-red-600">{a.message}</p>)}
        </div>
      )}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => (
          <Card key={s.label}><CardContent>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-wisestay-50 rounded-lg"><s.icon className="w-5 h-5 text-wisestay-600" /></div>
              <div><p className="text-xs text-gray-500">{s.label}</p><p className="text-xl font-bold">{s.value}</p>{s.change && <p className="text-xs text-green-600">{s.change}</p>}</div>
            </div>
          </CardContent></Card>
        ))}
      </div>
      {data.payouts.pending_amount > 0 && (
        <Card><CardContent><div className="flex justify-between items-center"><div><p className="text-sm text-gray-500">Pending Payout</p><p className="text-xl font-bold">${data.payouts.pending_amount.toLocaleString()}</p></div><p className="text-sm text-gray-500">Next: {data.payouts.next_payout_date}</p></div></CardContent></Card>
      )}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuthStore();
  return user?.role === 'owner' ? <OwnerDashboard /> : <GuestDashboard />;
}
