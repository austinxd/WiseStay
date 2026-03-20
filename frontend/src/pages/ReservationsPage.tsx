import { useOwnerReservations } from '@/hooks/useOwnerReservations';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';

export function ReservationsPage() {
  const { data, isLoading } = useOwnerReservations();
  if (isLoading) return <PageSpinner />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Reservations</h1>
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500"><tr>
            <th className="px-4 py-3 text-left">Code</th><th className="px-4 py-3 text-left">Guest</th><th className="px-4 py-3 text-left">Property</th><th className="px-4 py-3 text-left">Dates</th><th className="px-4 py-3 text-left">Channel</th><th className="px-4 py-3 text-left">Status</th><th className="px-4 py-3 text-right">Amount</th>
          </tr></thead>
          <tbody className="divide-y">{data?.results?.map(r => (
            <tr key={r.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-mono text-xs">{r.confirmation_code}</td>
              <td className="px-4 py-3">{r.guest_name}</td>
              <td className="px-4 py-3">{r.property_name}</td>
              <td className="px-4 py-3 text-gray-500">{r.check_in_date} → {r.check_out_date}</td>
              <td className="px-4 py-3 capitalize">{r.channel}</td>
              <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
              <td className="px-4 py-3 text-right font-medium">${r.total_amount}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
