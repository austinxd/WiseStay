import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  MapPin,
  Users,
  Bed,
  Bath,
  Wifi,
  Car,
  Waves,
  ThermometerSun,
  ArrowRight,
  Star,
  Shield,
  Smartphone,
  Search,
} from 'lucide-react';
import { useProperties } from '@/hooks/useProperties';

export function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState('2');
  const { data: propertiesData, isLoading } = useProperties({ page: 1 });

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (checkIn) params.set('check_in', checkIn);
    if (checkOut) params.set('check_out', checkOut);
    if (guests) params.set('guests', guests);
    navigate(`/properties?${params.toString()}`);
  };

  return (
    <div>
      {/* Compact Hero + Search */}
      <section className="bg-neutral-900 py-10 lg:py-14">
        <div className="container-page">
          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="text-2xl lg:text-3xl font-display font-bold text-white mb-2">
              Premium Vacation Rentals in Florida
            </h1>
            <p className="text-neutral-400">
              Book direct and save up to 17% vs Airbnb
            </p>
          </div>

          {/* Search Box */}
          <div className="bg-white rounded-xl p-4 lg:p-5 max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1.5">Check-in</label>
                <input
                  type="date"
                  value={checkIn}
                  onChange={(e) => setCheckIn(e.target.value)}
                  className="w-full px-3 py-2.5 bg-neutral-50 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:border-neutral-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1.5">Check-out</label>
                <input
                  type="date"
                  value={checkOut}
                  onChange={(e) => setCheckOut(e.target.value)}
                  className="w-full px-3 py-2.5 bg-neutral-50 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:border-neutral-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1.5">Guests</label>
                <select
                  value={guests}
                  onChange={(e) => setGuests(e.target.value)}
                  className="w-full px-3 py-2.5 bg-neutral-50 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:border-neutral-400"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16].map(n => (
                    <option key={n} value={n}>{n} {n === 1 ? 'guest' : 'guests'}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleSearch}
                  className="w-full bg-brand-gold text-white font-medium py-2.5 px-4 rounded-lg hover:bg-opacity-90 transition-colors flex items-center justify-center gap-2"
                >
                  <Search className="w-4 h-4" />
                  Search
                </button>
              </div>
            </div>
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-8 text-white/50 text-sm">
            <div className="flex items-center gap-2"><Shield className="w-4 h-4" /> Verified Properties</div>
            <div className="flex items-center gap-2"><Key className="w-4 h-4" /> Smart Lock Access</div>
            <div className="flex items-center gap-2"><Star className="w-4 h-4" /> 4.9 Average Rating</div>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent" />
      </section>

      {/* Features Bar */}
      <section className="py-6 border-b border-neutral-100">
        <div className="container-page">
          <div className="flex flex-wrap justify-center gap-6 lg:gap-12">
            {[
              { icon: Waves, label: 'Pool & Jacuzzi' },
              { icon: Wifi, label: 'High-Speed WiFi' },
              { icon: Car, label: 'Free Parking' },
              { icon: ThermometerSun, label: 'Climate Control' },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-neutral-600">
                <Icon className="w-5 h-5" />
                <span className="text-sm font-medium">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Properties Grid */}
      <section className="py-12 lg:py-16">
        <div className="container-page">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl lg:text-3xl font-display font-bold text-neutral-900">
              {t('home.featured.title')}
            </h2>
            <Link
              to="/properties"
              className="hidden md:flex items-center gap-2 text-neutral-600 hover:text-neutral-900 font-medium transition-colors"
            >
              View all
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="card animate-pulse">
                  <div className="h-48 bg-neutral-200" />
                  <div className="p-4 space-y-3">
                    <div className="h-4 bg-neutral-200 rounded w-3/4" />
                    <div className="h-3 bg-neutral-200 rounded w-1/2" />
                    <div className="h-3 bg-neutral-200 rounded w-1/4" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {propertiesData?.results?.slice(0, 8).map((property) => (
                <Link
                  key={property.id}
                  to={`/properties/${property.slug}`}
                  className="card group"
                >
                  {/* Image */}
                  <div className="relative h-48 overflow-hidden">
                    {property.images?.[0] ? (
                      <img
                        src={property.images[0].url}
                        alt={property.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    ) : (
                      <div className="w-full h-full bg-neutral-200 flex items-center justify-center">
                        <MapPin className="w-10 h-10 text-neutral-400" />
                      </div>
                    )}
                    {/* Price Badge */}
                    <div className="absolute top-3 right-3 bg-white/95 backdrop-blur-sm px-2.5 py-1 rounded-lg shadow-sm">
                      <span className="font-bold text-neutral-900">${property.base_nightly_rate}</span>
                      <span className="text-neutral-500 text-xs"> /night</span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4">
                    <h3 className="font-semibold text-neutral-900 mb-1 group-hover:text-brand-gold transition-colors line-clamp-1">
                      {property.name}
                    </h3>
                    <div className="flex items-center gap-1 text-neutral-500 text-sm mb-3">
                      <MapPin className="w-3.5 h-3.5" />
                      <span>{property.city}, {property.state}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-neutral-600">
                      <span className="flex items-center gap-1">
                        <Bed className="w-3.5 h-3.5" />
                        {property.bedrooms} BR
                      </span>
                      <span className="flex items-center gap-1">
                        <Bath className="w-3.5 h-3.5" />
                        {property.bathrooms} BA
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        {property.max_guests}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          <div className="text-center mt-8 md:hidden">
            <Link to="/properties" className="btn-secondary">
              View all properties
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </div>
        </div>
      </section>

      {/* Why Book Direct */}
      <section className="py-12 lg:py-16 bg-neutral-50">
        <div className="container-page">
          <h2 className="text-2xl lg:text-3xl font-display font-bold text-neutral-900 text-center mb-10">
            Why Book Direct?
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              {
                icon: Star,
                title: 'Save 17%',
                desc: 'No platform fees. Pay the owner directly and keep more money in your pocket.',
              },
              {
                icon: Shield,
                title: 'Secure Booking',
                desc: 'Protected payments and verified properties for peace of mind.',
              },
              {
                icon: Smartphone,
                title: 'Smart Access',
                desc: 'Keyless entry, climate control, and 24/7 support via our app.',
              },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="text-center">
                <div className="w-14 h-14 bg-white rounded-xl shadow-card flex items-center justify-center mx-auto mb-4">
                  <Icon className="w-6 h-6 text-brand-gold" />
                </div>
                <h3 className="font-semibold text-neutral-900 mb-2">{title}</h3>
                <p className="text-neutral-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-12 lg:py-16">
        <div className="container-page">
          <div className="bg-neutral-900 rounded-2xl p-8 lg:p-12 text-center">
            <h2 className="text-2xl lg:text-3xl font-display font-bold text-white mb-3">
              Ready to book your next getaway?
            </h2>
            <p className="text-neutral-400 mb-6 max-w-xl mx-auto">
              Browse our collection of premium vacation rentals and start saving today.
            </p>
            <Link to="/properties" className="btn-gold">
              Browse Properties
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
