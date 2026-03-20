import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Search, DollarSign, Trophy, Home, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useProperties } from '@/hooks/useProperties';
import { CardSkeleton } from '@/components/ui/Skeleton';

export function HomePage() {
  const navigate = useNavigate();
  const [city, setCity] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState('2');
  const { data: propertiesData, isLoading } = useProperties({ page: 1 });

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (city) params.set('city', city);
    if (checkIn) params.set('check_in', checkIn);
    if (checkOut) params.set('check_out', checkOut);
    if (guests) params.set('guests', guests);
    navigate(`/properties?${params.toString()}`);
  };

  return (
    <div>
      {/* Hero */}
      <section className="relative bg-gradient-to-br from-wisestay-800 to-wisestay-600 text-white">
        <div className="container-page py-20 md:py-32 text-center">
          <h1 className="text-4xl md:text-6xl font-heading font-bold mb-4">Premium Vacation Rentals,<br />Without the Markup</h1>
          <p className="text-lg md:text-xl text-wisestay-100 mb-10 max-w-2xl mx-auto">Book directly. Earn rewards. Experience smart living.</p>

          {/* Search Bar */}
          <div className="bg-white rounded-xl shadow-2xl p-4 max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              <input type="text" placeholder="Where? (e.g. Miami)" value={city} onChange={e => setCity(e.target.value)} className="px-4 py-3 border border-gray-200 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-wisestay-300" />
              <input type="date" placeholder="Check-in" value={checkIn} onChange={e => setCheckIn(e.target.value)} className="px-4 py-3 border border-gray-200 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-wisestay-300" />
              <input type="date" placeholder="Check-out" value={checkOut} onChange={e => setCheckOut(e.target.value)} className="px-4 py-3 border border-gray-200 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-wisestay-300" />
              <input type="number" min="1" max="16" placeholder="Guests" value={guests} onChange={e => setGuests(e.target.value)} className="px-4 py-3 border border-gray-200 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-wisestay-300" />
              <Button size="lg" onClick={handleSearch} className="flex items-center justify-center gap-2"><Search className="w-5 h-5" /> Search</Button>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Properties */}
      <section className="container-page py-16">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl md:text-3xl font-heading font-bold">Featured Stays</h2>
          <Link to="/properties" className="text-wisestay-600 hover:text-wisestay-700 font-medium text-sm flex items-center gap-1">View all <ArrowRight className="w-4 h-4" /></Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)
          ) : (
            propertiesData?.results?.slice(0, 6).map(property => (
              <Link key={property.id} to={`/properties/${property.slug}`} className="group">
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
                  <div className="aspect-[4/3] bg-gray-100 overflow-hidden">
                    {property.images?.[0] && <img src={property.images[0].url} alt={property.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />}
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900">{property.name}</h3>
                    <p className="text-sm text-gray-500">{property.city}, {property.state}</p>
                    <div className="flex items-center gap-3 mt-2 text-sm text-gray-600">
                      <span>{property.bedrooms} BR</span>
                      <span>&middot;</span>
                      <span>{property.max_guests} guests</span>
                    </div>
                    <p className="mt-2 font-semibold text-wisestay-700">${property.base_nightly_rate}<span className="text-gray-400 font-normal text-sm"> /night</span></p>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </section>

      {/* Why Book Direct */}
      <section className="bg-gray-50 py-16">
        <div className="container-page">
          <h2 className="text-2xl md:text-3xl font-heading font-bold text-center mb-12">Why Book Direct</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: DollarSign, title: 'Save Up to 15%', desc: 'No Airbnb service fees. Our prices are lower because you book directly with us.' },
              { icon: Trophy, title: 'Earn Rewards', desc: 'Every stay earns loyalty points. Redeem for discounts on future trips.' },
              { icon: Home, title: 'Smart Home Experience', desc: 'Keyless entry, climate control, and an AI concierge — all automated.' },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-white rounded-xl p-8 text-center shadow-sm border border-gray-100">
                <div className="w-12 h-12 bg-wisestay-50 rounded-xl flex items-center justify-center mx-auto mb-4"><Icon className="w-6 h-6 text-wisestay-600" /></div>
                <h3 className="font-semibold text-lg mb-2">{title}</h3>
                <p className="text-sm text-gray-600">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Loyalty Teaser */}
      <section className="container-page py-16">
        <div className="bg-gradient-to-r from-wisestay-600 to-wisestay-800 rounded-2xl p-8 md:p-12 text-white text-center">
          <h2 className="text-2xl md:text-3xl font-heading font-bold mb-3">WiseStay Rewards</h2>
          <p className="text-wisestay-100 mb-2">Bronze &rarr; Silver &rarr; Gold &rarr; Platinum</p>
          <p className="text-wisestay-200 mb-6 max-w-lg mx-auto">Earn points. Unlock perks. Save more with every stay.</p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/loyalty-program"><Button variant="outline" className="border-white text-white hover:bg-white/10">Learn More</Button></Link>
            <Link to="/register"><Button className="bg-white text-wisestay-700 hover:bg-wisestay-50">Sign Up Free</Button></Link>
          </div>
        </div>
      </section>
    </div>
  );
}
