import { Link } from 'react-router-dom';
import { useTiers } from '@/hooks/useLoyalty';
import { Button } from '@/components/ui/Button';
import { Trophy, Check } from 'lucide-react';

export function LoyaltyProgramPage() {
  const { data: tiers } = useTiers();
  return (
    <div className="container-page py-16">
      <div className="text-center mb-12">
        <Trophy className="w-12 h-12 text-accent-500 mx-auto mb-4" />
        <h1 className="text-3xl font-heading font-bold mb-3">WiseStay Rewards</h1>
        <p className="text-gray-600 max-w-lg mx-auto">Earn points on every direct booking. Climb tiers for exclusive perks.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        {tiers?.map(t => (
          <div key={t.tier_name} className="bg-white rounded-xl border p-6 text-center">
            <h3 className="text-lg font-bold capitalize mb-2">{t.tier_name}</h3>
            <p className="text-3xl font-bold text-wisestay-600 mb-1">{t.discount_percent}%</p>
            <p className="text-sm text-gray-500 mb-4">discount on bookings</p>
            <ul className="text-sm space-y-2 text-left">
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> {t.min_reservations}+ bookings</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> {t.min_referrals}+ referrals</li>
              {t.early_checkin && <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> Early check-in</li>}
              {t.late_checkout && <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> Late checkout</li>}
              {t.priority_support && <li className="flex items-center gap-2"><Check className="w-4 h-4 text-green-500" /> Priority support</li>}
            </ul>
          </div>
        ))}
      </div>
      <div className="text-center"><Link to="/register"><Button size="lg">Join WiseStay Rewards</Button></Link></div>
    </div>
  );
}
