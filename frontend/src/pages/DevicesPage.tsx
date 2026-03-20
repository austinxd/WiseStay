import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ownerService } from '@/services/ownerService';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { Wifi, Lock, Thermometer, Volume2 } from 'lucide-react';

const icons: Record<string, any> = { smart_lock: Lock, thermostat: Thermometer, noise_sensor: Volume2 };

export function DevicesPage() {
  const { propertyId } = useParams();
  const { data, isLoading } = useQuery({ queryKey: ['devices', propertyId], queryFn: () => ownerService.getDevices(Number(propertyId)), enabled: !!propertyId });
  if (isLoading) return <PageSpinner />;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Devices</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{data?.map(d => {
        const Icon = icons[d.device_type] || Wifi;
        return (
          <Card key={d.id}><CardContent>
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gray-100 rounded-xl"><Icon className="w-6 h-6 text-gray-600" /></div>
              <div className="flex-1">
                <h3 className="font-medium">{d.display_name}</h3>
                <p className="text-xs text-gray-500 capitalize">{d.brand} {d.device_type.replace('_',' ')}</p>
              </div>
              <StatusBadge status={d.status} />
            </div>
            {d.battery_level !== null && <div className="mt-3"><div className="flex justify-between text-xs mb-1"><span>Battery</span><span>{d.battery_level}%</span></div><div className="h-2 bg-gray-200 rounded-full"><div className={`h-full rounded-full ${d.battery_level > 20 ? 'bg-green-500' : 'bg-red-500'}`} style={{width: `${d.battery_level}%`}} /></div></div>}
          </CardContent></Card>
        );
      })}</div>
    </div>
  );
}
