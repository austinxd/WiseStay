import { Link } from 'react-router-dom';
import { useOwnerPayouts } from '@/hooks/useOwnerPayouts';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';

export function PayoutsPage() {
  const { data, isLoading } = useOwnerPayouts();
  if (isLoading) return <PageSpinner />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Payouts</h1>
      <div className="space-y-4">{data?.results?.map(p => (
        <Link key={p.id} to={`/payouts/${p.id}`}><Card className="hover:shadow-md"><CardContent>
          <div className="flex items-center justify-between">
            <div><p className="font-medium">{p.period_year}-{String(p.period_month).padStart(2,'0')}</p><p className="text-sm text-gray-500">Gross: ${p.gross_revenue} &middot; Net: ${p.net_amount}</p></div>
            <div className="text-right"><StatusBadge status={p.status} />{p.paid_at && <p className="text-xs text-gray-400 mt-1">Paid {new Date(p.paid_at).toLocaleDateString()}</p>}</div>
          </div>
        </CardContent></Card></Link>
      ))}</div>
    </div>
  );
}
