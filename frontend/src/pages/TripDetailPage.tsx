import { useParams } from 'react-router-dom';
import { useReservation } from '@/hooks/useReservations';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';

export function TripDetailPage() {
  const { id } = useParams();
  const { data: res, isLoading } = useReservation(Number(id));
  if (isLoading) return <PageSpinner />;
  if (!res) return <div>Reservation not found</div>;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-heading font-bold">{res.confirmation_code}</h1><StatusBadge status={res.status} /></div>
      <Card><CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><p className="text-gray-500">Property</p><p className="font-medium">{res.property_name}</p></div>
          <div><p className="text-gray-500">Dates</p><p className="font-medium">{res.check_in_date} → {res.check_out_date}</p></div>
          <div><p className="text-gray-500">Guests</p><p className="font-medium">{res.guests_count}</p></div>
          <div><p className="text-gray-500">Total</p><p className="font-medium">${res.total_amount}</p></div>
          {res.discount_amount > 0 && <div><p className="text-gray-500">Discount</p><p className="font-medium text-green-600">-${res.discount_amount}</p></div>}
          {res.points_earned > 0 && <div><p className="text-gray-500">Points Earned</p><p className="font-medium text-accent-600">+{res.points_earned}</p></div>}
        </div>
      </CardContent></Card>
      {res.guest_notes && <Card><CardHeader><h3 className="font-semibold">Your Notes</h3></CardHeader><CardContent><p className="text-sm text-gray-600">{res.guest_notes}</p></CardContent></Card>}
    </div>
  );
}
