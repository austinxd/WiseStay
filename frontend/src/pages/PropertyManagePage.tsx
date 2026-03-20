import { useParams } from 'react-router-dom';
import { usePropertyPerformance } from '@/hooks/useOwnerDashboard';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { PageSpinner } from '@/components/ui/Spinner';
import { StatusBadge } from '@/components/ui/Badge';

export function PropertyManagePage() {
  const { id } = useParams();
  const { data, isLoading } = usePropertyPerformance(Number(id));
  if (isLoading) return <PageSpinner />;
  if (!data) return <div>Not found</div>;
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        {data.property.cover_image_url && <img src={data.property.cover_image_url} className="w-16 h-16 rounded-xl object-cover" />}
        <div><h1 className="text-2xl font-heading font-bold">{data.property.name}</h1><p className="text-gray-500">{data.property.city}</p></div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card><CardContent><p className="text-xs text-gray-500">Revenue</p><p className="text-xl font-bold">${data.revenue.total.toLocaleString()}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Net to You</p><p className="text-xl font-bold">${data.revenue.net_to_owner.toLocaleString()}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Occupancy</p><p className="text-xl font-bold">{data.occupancy.total_percent}%</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Reservations</p><p className="text-xl font-bold">{data.reservations.total}</p></CardContent></Card>
      </div>
      {data.devices.length > 0 && (
        <Card><CardHeader><h3 className="font-semibold">Devices</h3></CardHeader><CardContent>
          <div className="space-y-2">{data.devices.map(d => (
            <div key={d.id} className="flex justify-between items-center text-sm"><span>{d.display_name}</span><StatusBadge status={d.status} /></div>
          ))}</div>
        </CardContent></Card>
      )}
    </div>
  );
}
