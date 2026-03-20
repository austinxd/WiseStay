import { Link } from 'react-router-dom';
import { useOwnerProperties } from '@/hooks/useOwnerDashboard';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { Home } from 'lucide-react';

export function MyPropertiesPage() {
  const { data, isLoading } = useOwnerProperties();
  if (isLoading) return <PageSpinner />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">My Properties</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data?.results?.map(p => (
          <Link key={p.id} to={`/my-properties/${p.id}`}>
            <Card className="hover:shadow-md">
              <div className="aspect-[4/3] bg-gray-100 rounded-t-xl overflow-hidden">
                {p.cover_image_url ? <img src={p.cover_image_url} className="w-full h-full object-cover" /> : <div className="flex items-center justify-center h-full"><Home className="w-12 h-12 text-gray-300" /></div>}
              </div>
              <CardContent>
                <div className="flex justify-between items-start"><h3 className="font-semibold">{p.name}</h3><StatusBadge status={p.status} /></div>
                <p className="text-sm text-gray-500">{p.city}, {p.state}</p>
                <div className="flex gap-4 mt-2 text-xs text-gray-400">
                  <span>{p.active_reservations_count || 0} active bookings</span>
                  <span>{p.devices_count || 0} devices</span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
