import { useParams } from 'react-router-dom';
import { useOwnerPayout } from '@/hooks/useOwnerPayouts';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';

export function PayoutDetailPage() {
  const { id } = useParams();
  const { data, isLoading } = useOwnerPayout(Number(id));
  if (isLoading) return <PageSpinner />;
  if (!data) return <div>Not found</div>;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-heading font-bold">Payout — {data.period_year}-{String(data.period_month).padStart(2,'0')}</h1><StatusBadge status={data.status} /></div>
      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent><p className="text-xs text-gray-500">Gross</p><p className="text-xl font-bold">${data.gross_revenue}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Commission</p><p className="text-xl font-bold text-red-600">-${data.commission_amount}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Net</p><p className="text-xl font-bold text-green-600">${data.net_amount}</p></CardContent></Card>
      </div>
      {data.line_items && (
        <Card><CardHeader><h3 className="font-semibold">Reservations</h3></CardHeader><CardContent>
          <table className="w-full text-sm"><thead className="text-gray-500 border-b"><tr><th className="pb-2 text-left">Guest</th><th className="pb-2 text-left">Dates</th><th className="pb-2 text-left">Channel</th><th className="pb-2 text-right">Total</th><th className="pb-2 text-right">Your Share</th></tr></thead>
          <tbody className="divide-y">{data.line_items.map((li, i) => (
            <tr key={i}><td className="py-2">{li.guest_name}</td><td className="py-2 text-gray-500">{li.check_in_date} → {li.check_out_date}</td><td className="py-2 capitalize">{li.channel}</td><td className="py-2 text-right">${li.reservation_total}</td><td className="py-2 text-right font-medium">${li.owner_amount}</td></tr>
          ))}</tbody></table>
        </CardContent></Card>
      )}
    </div>
  );
}
