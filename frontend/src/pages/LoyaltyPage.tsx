import { useLoyaltyDashboard, usePointsHistory, useReferralStats } from '@/hooks/useLoyalty';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { PageSpinner } from '@/components/ui/Spinner';
import { Trophy, Gift, ArrowUp } from 'lucide-react';

export function LoyaltyPage() {
  const { data: loyalty, isLoading } = useLoyaltyDashboard();
  const { data: history } = usePointsHistory();
  const { data: referrals } = useReferralStats();
  if (isLoading) return <PageSpinner />;
  if (!loyalty) return null;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Loyalty & Rewards</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card><CardContent className="text-center">
          <Trophy className="w-10 h-10 text-accent-500 mx-auto mb-2" />
          <p className="text-2xl font-bold capitalize">{loyalty.tier}</p><p className="text-sm text-gray-500">Current Tier</p>
          {loyalty.next_tier && <p className="text-xs text-gray-400 mt-1">Next: {loyalty.next_tier.name} ({loyalty.next_tier.reservations_needed} more bookings)</p>}
        </CardContent></Card>
        <Card><CardContent className="text-center">
          <p className="text-3xl font-bold text-wisestay-600">{loyalty.points_balance}</p><p className="text-sm text-gray-500">Points Available</p>
          {loyalty.points_expiring_soon && <p className="text-xs text-red-500 mt-1">{loyalty.points_expiring_soon.amount} expiring soon</p>}
        </CardContent></Card>
        <Card><CardContent className="text-center">
          <Gift className="w-10 h-10 text-wisestay-400 mx-auto mb-2" />
          <p className="text-lg font-bold font-mono">{loyalty.referral_code}</p><p className="text-sm text-gray-500">Your Referral Code</p>
        </CardContent></Card>
      </div>
      {history?.results && (
        <Card><CardHeader><h3 className="font-semibold">Points History</h3></CardHeader><CardContent>
          <div className="space-y-3">{history.results.slice(0,10).map(t => (
            <div key={t.id} className="flex justify-between items-center text-sm">
              <div><p className="font-medium">{t.description}</p><p className="text-gray-400 text-xs">{new Date(t.created_at).toLocaleDateString()}</p></div>
              <span className={`font-bold ${t.points > 0 ? 'text-green-600' : 'text-red-600'}`}>{t.points > 0 ? '+' : ''}{t.points}</span>
            </div>
          ))}</div>
        </CardContent></Card>
      )}
      {referrals && (
        <Card><CardHeader><h3 className="font-semibold">Referral Stats</h3></CardHeader><CardContent>
          <div className="grid grid-cols-3 gap-4 text-center text-sm">
            <div><p className="text-2xl font-bold">{referrals.completed}</p><p className="text-gray-500">Completed</p></div>
            <div><p className="text-2xl font-bold">{referrals.pending}</p><p className="text-gray-500">Pending</p></div>
            <div><p className="text-2xl font-bold">{referrals.total_bonus_points_earned}</p><p className="text-gray-500">Bonus Points</p></div>
          </div>
        </CardContent></Card>
      )}
    </div>
  );
}
