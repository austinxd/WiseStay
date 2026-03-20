import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ownerService } from '@/services/ownerService';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { PageSpinner } from '@/components/ui/Spinner';

export function RevenuePage() {
  const [year] = useState(new Date().getFullYear());
  const { data, isLoading } = useQuery({ queryKey: ['revenue', year], queryFn: () => ownerService.getRevenue(year) });
  if (isLoading) return <PageSpinner />;
  if (!data) return null;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Revenue Report — {data.period}</h1>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card><CardContent><p className="text-xs text-gray-500">Gross Revenue</p><p className="text-xl font-bold">${data.totals.gross_revenue.toLocaleString()}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Commission</p><p className="text-xl font-bold text-red-600">-${data.totals.total_commission.toLocaleString()}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Net Revenue</p><p className="text-xl font-bold text-green-600">${data.totals.total_net.toLocaleString()}</p></CardContent></Card>
        <Card><CardContent><p className="text-xs text-gray-500">Reservations</p><p className="text-xl font-bold">{data.totals.total_reservations}</p></CardContent></Card>
      </div>
      {data.properties.map(p => (
        <Card key={p.property_id}><CardHeader><h3 className="font-semibold">{p.property_name}</h3></CardHeader><CardContent>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div><p className="text-gray-500">Gross</p><p className="font-medium">${p.gross_revenue.toLocaleString()}</p></div>
            <div><p className="text-gray-500">Commission ({(p.commission_rate * 100).toFixed(0)}%)</p><p className="font-medium">-${p.commission_amount.toLocaleString()}</p></div>
            <div><p className="text-gray-500">Net</p><p className="font-medium text-green-600">${p.net_revenue.toLocaleString()}</p></div>
          </div>
        </CardContent></Card>
      ))}
    </div>
  );
}
