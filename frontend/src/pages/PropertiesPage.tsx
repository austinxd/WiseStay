import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useProperties } from '@/hooks/useProperties';
import { CardSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { Pagination } from '@/components/ui/Pagination';
import { MapPin, Bed, Bath, Users, Search } from 'lucide-react';

export function PropertiesPage() {
  const { t } = useTranslation();
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
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <div className="bg-white border-b border-neutral-100">
        <div className="container-page py-8">
          <h1 className="text-3xl font-display font-bold text-neutral-900 mb-2">
            {params.city ? `Properties in ${params.city}` : t('properties.title')}
          </h1>
          {data && (
            <p className="text-neutral-500">
              {data.count} {data.count === 1 ? 'property' : 'properties'} available
            </p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border-b border-neutral-100">
        <div className="container-page py-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <input
              type="text"
              placeholder="City"
              value={params.city || ''}
              onChange={e => updateFilter('city', e.target.value)}
              className="input"
            />
            <input
              type="date"
              placeholder="Check-in"
              value={params.check_in || ''}
              onChange={e => updateFilter('check_in', e.target.value)}
              className="input"
            />
            <input
              type="date"
              placeholder="Check-out"
              value={params.check_out || ''}
              onChange={e => updateFilter('check_out', e.target.value)}
              className="input"
            />
            <select
              value={params.guests || ''}
              onChange={e => updateFilter('guests', e.target.value)}
              className="input"
            >
              <option value="">Guests</option>
              {[1, 2, 3, 4, 5, 6, 8, 10, 12].map(n => (
                <option key={n} value={n}>{n} guests</option>
              ))}
            </select>
            <select
              value={params.property_type || ''}
              onChange={e => updateFilter('property_type', e.target.value)}
              className="input"
            >
              <option value="">All types</option>
              <option value="house">House</option>
              <option value="apartment">Apartment</option>
              <option value="condo">Condo</option>
              <option value="villa">Villa</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="container-page py-8">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 9 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        ) : !data?.results?.length ? (
          <EmptyState
            icon={<Search className="w-12 h-12" />}
            title={t('properties.empty.title')}
            description={t('properties.empty.description')}
            action={{ label: t('properties.filters.clear_filters'), onClick: () => setSearchParams({}) }}
          />
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {data.results.map(property => (
                <Link key={property.id} to={`/properties/${property.slug}`} className="card group">
                  {/* Image */}
                  <div className="relative h-64 overflow-hidden">
                    {property.images?.[0] ? (
                      <img
                        src={property.images[0].url}
                        alt={property.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    ) : (
                      <div className="w-full h-full bg-neutral-200 flex items-center justify-center">
                        <MapPin className="w-12 h-12 text-neutral-400" />
                      </div>
                    )}
                    {/* Price Badge */}
                    <div className="absolute top-4 right-4 bg-white px-3 py-1.5 rounded-lg shadow-sm">
                      <span className="font-bold text-neutral-900">${property.base_nightly_rate}</span>
                      <span className="text-neutral-500 text-sm"> / night</span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-5">
                    <h3 className="font-semibold text-lg text-neutral-900 mb-2 group-hover:text-brand-gold transition-colors">
                      {property.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-neutral-500 mb-4">
                      <MapPin className="w-4 h-4" />
                      <span className="text-sm">{property.city}, {property.state}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-neutral-600">
                      <div className="flex items-center gap-1.5">
                        <Bed className="w-4 h-4" />
                        <span>{property.bedrooms} BR</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Bath className="w-4 h-4" />
                        <span>{property.bathrooms} BA</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Users className="w-4 h-4" />
                        <span>{property.max_guests}</span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            <Pagination
              currentPage={page}
              totalPages={Math.ceil((data.count || 0) / 12)}
              onPageChange={p => {
                const next = new URLSearchParams(searchParams);
                next.set('page', String(p));
                setSearchParams(next);
                window.scrollTo(0, 0);
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}
