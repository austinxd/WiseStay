import { useSearchParams, Link } from 'react-router-dom';
import { useProperties } from '@/hooks/useProperties';
import { CardSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { Pagination } from '@/components/ui/Pagination';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Search } from 'lucide-react';

export function PropertiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const params: Record<string, string> = {};
  searchParams.forEach((v, k) => { params[k] = v; });
  const page = parseInt(params.page || '1');

  const { data, isLoading } = useProperties({ ...params, page });

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    next.delete('page');
    setSearchParams(next);
  };

  return (
    <div className="container-page py-8">
      <h1 className="text-2xl font-heading font-bold mb-6">
        {params.city ? `Properties in ${params.city}` : 'All Properties'}
        {data && <span className="text-gray-400 font-normal text-lg ml-2">({data.count})</span>}
      </h1>

      {/* Filters */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
        <Input placeholder="City" value={params.city || ''} onChange={e => updateFilter('city', e.target.value)} />
        <Input type="date" placeholder="Check-in" value={params.check_in || ''} onChange={e => updateFilter('check_in', e.target.value)} />
        <Input type="date" placeholder="Check-out" value={params.check_out || ''} onChange={e => updateFilter('check_out', e.target.value)} />
        <Input type="number" placeholder="Guests" min="1" value={params.guests || ''} onChange={e => updateFilter('guests', e.target.value)} />
        <Select options={[{value:'',label:'Any type'},{value:'house',label:'House'},{value:'apartment',label:'Apartment'},{value:'condo',label:'Condo'},{value:'villa',label:'Villa'},{value:'cabin',label:'Cabin'}]} value={params.property_type || ''} onChange={e => updateFilter('property_type', e.target.value)} />
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({length: 9}).map((_,i) => <CardSkeleton key={i} />)}
        </div>
      ) : !data?.results?.length ? (
        <EmptyState title="No properties found" description="Try adjusting your filters" action={{ label: 'Clear Filters', onClick: () => setSearchParams({}) }} />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.results.map(p => (
              <Link key={p.id} to={`/properties/${p.slug}`} className="group">
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
                  <div className="aspect-[4/3] bg-gray-100 overflow-hidden">
                    {p.images?.[0] && <img src={p.images[0].url} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />}
                  </div>
                  <div className="p-4">
                    {p.is_direct_booking_enabled && <span className="inline-block text-xs font-medium bg-wisestay-50 text-wisestay-700 px-2 py-0.5 rounded mb-2">Direct Booking</span>}
                    <h3 className="font-semibold text-gray-900">{p.name}</h3>
                    <p className="text-sm text-gray-500">{p.city}, {p.state}</p>
                    <div className="flex items-center gap-2 mt-2 text-sm text-gray-600">
                      <span>{p.bedrooms} BR</span><span>&middot;</span><span>{p.bathrooms} BA</span><span>&middot;</span><span>{p.max_guests} guests</span>
                    </div>
                    <p className="mt-2 font-semibold text-wisestay-700">${p.base_nightly_rate}<span className="text-gray-400 font-normal text-sm"> /night</span></p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
          <Pagination currentPage={page} totalPages={Math.ceil((data.count || 0) / 12)} onPageChange={p => { const next = new URLSearchParams(searchParams); next.set('page', String(p)); setSearchParams(next); window.scrollTo(0,0); }} />
        </>
      )}
    </div>
  );
}
