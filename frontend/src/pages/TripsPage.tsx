import { Link } from 'react-router-dom';
import { useMyReservations } from '@/hooks/useReservations';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Plane } from 'lucide-react';

export function TripsPage() {
  const { data, isLoading } = useMyReservations();
  if (isLoading) return <PageSpinner />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">My Trips</h1>
      {!data?.results?.length ? (
        <EmptyState icon={<Plane className="w-12 h-12" />} title="No trips yet" description="Start exploring properties for your next getaway." action={{ label: 'Browse Properties', onClick: () => window.location.href = '/properties' }} />
      ) : (
        <div className="space-y-4">
          {data.results.map(r => (
            <Link key={r.id} to={`/trips/${r.id}`}>
              <Card className="hover:shadow-md"><CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{r.property_name || r.confirmation_code}</h3>
                    <p className="text-sm text-gray-500">{r.check_in_date} → {r.check_out_date} &middot; {r.nights} nights</p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={r.status} />
                    <p className="text-sm font-medium mt-1">${r.total_amount}</p>
                  </div>
                </div>
              </CardContent></Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
