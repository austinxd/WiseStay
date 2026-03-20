import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Search, MapPin, Calendar, Users, Star, ArrowRight, Shield, Sparkles, Wifi, Key, ThermometerSun, ChevronRight, Phone, MessageCircle, Quote } from 'lucide-react';
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
    <div className="overflow-hidden">
      {/* HERO */}
      <section className="relative min-h-screen flex items-center justify-center">
        <div className="absolute inset-0 bg-navy-950">
          <div className="absolute inset-0 bg-cover bg-center opacity-40" style={{ backgroundImage: 'url(https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=1920&q=80)' }} />
          <div className="absolute inset-0 bg-gradient-to-b from-navy-950/60 via-navy-950/30 to-navy-950/80" />
        </div>

        <div className="relative z-10 container-page text-center pt-32 pb-20">
          <div className="animate-in inline-flex items-center gap-2 bg-white/10 backdrop-blur-md border border-white/20 text-white/90 px-5 py-2 rounded-full text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4 text-accent-400" /> Premium Vacation Rentals in the USA
          </div>

          <h1 className="animate-in animate-in-delay-1 text-4xl sm:text-5xl md:text-7xl font-heading font-bold text-white leading-[1.1] mb-6 max-w-4xl mx-auto">
            Your Next Escape,{' '}<span className="italic text-accent-400">Without</span>{' '}the Markup
          </h1>

          <p className="animate-in animate-in-delay-2 text-lg md:text-xl text-white/70 mb-12 max-w-2xl mx-auto leading-relaxed">
            Book directly with WiseStay. Save up to 15% versus Airbnb. Earn rewards. Experience smart-home luxury on every stay.
          </p>

          {/* Search Bar */}
          <div className="animate-in animate-in-delay-3 max-w-5xl mx-auto">
            <div className="glass rounded-3xl p-3 shadow-elevated">
              <div className="grid grid-cols-1 md:grid-cols-12 gap-2">
                <div className="md:col-span-4 relative">
                  <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-400" />
                  <input type="text" placeholder="Where are you going?" value={city} onChange={e => setCity(e.target.value)} className="w-full pl-12 pr-4 py-4 bg-white rounded-2xl text-navy-900 text-sm font-medium placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent-400/50 border border-gray-100" />
                </div>
                <div className="md:col-span-2 relative">
                  <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-400 pointer-events-none" />
                  <input type="date" value={checkIn} onChange={e => setCheckIn(e.target.value)} className="w-full pl-12 pr-4 py-4 bg-white rounded-2xl text-navy-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent-400/50 border border-gray-100" />
                </div>
                <div className="md:col-span-2 relative">
                  <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-400 pointer-events-none" />
                  <input type="date" value={checkOut} onChange={e => setCheckOut(e.target.value)} className="w-full pl-12 pr-4 py-4 bg-white rounded-2xl text-navy-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent-400/50 border border-gray-100" />
                </div>
                <div className="md:col-span-2 relative">
                  <Users className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-400" />
                  <input type="number" min="1" max="16" placeholder="Guests" value={guests} onChange={e => setGuests(e.target.value)} className="w-full pl-12 pr-4 py-4 bg-white rounded-2xl text-navy-900 text-sm font-medium placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-accent-400/50 border border-gray-100" />
                </div>
                <div className="md:col-span-2">
                  <button onClick={handleSearch} className="w-full h-full min-h-[56px] bg-navy-900 hover:bg-navy-800 text-white rounded-2xl font-semibold transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-xl active:scale-[0.98]">
                    <Search className="w-5 h-5" /><span className="hidden sm:inline">Search</span>
                  </button>
                </div>
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

      {/* STATS BAR */}
      <section className="relative -mt-16 z-20 container-page">
        <div className="bg-white rounded-3xl shadow-elevated border border-gray-100 py-8 px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { number: '50+', label: 'Premium Properties' },
              { number: '2,000+', label: 'Happy Guests' },
              { number: '15%', label: 'Average Savings' },
              { number: '4.9', label: 'Guest Rating' },
            ].map(({ number, label }) => (
              <div key={label}>
                <p className="text-3xl md:text-4xl font-heading font-bold text-navy-900">{number}</p>
                <p className="text-sm text-gray-500 mt-1">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURED PROPERTIES */}
      <section className="container-page py-24">
        <div className="flex items-end justify-between mb-12">
          <div>
            <p className="text-accent-600 font-semibold text-sm uppercase tracking-widest mb-2">Curated Collection</p>
            <h2 className="text-3xl md:text-4xl font-heading font-bold text-navy-900">Featured Stays</h2>
          </div>
          <Link to="/properties" className="hidden md:flex items-center gap-2 text-navy-600 hover:text-accent-600 font-medium text-sm transition-colors group">
            View all properties <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)
          ) : (
            propertiesData?.results?.slice(0, 6).map((property, idx) => (
              <Link key={property.id} to={`/properties/${property.slug}`} className="group animate-in" style={{ animationDelay: `${idx * 0.1}s` }}>
                <div className="bg-white rounded-3xl overflow-hidden border border-gray-100 card-hover">
                  <div className="relative aspect-[4/3] overflow-hidden">
                    {property.images?.[0] ? (
                      <img src={property.images[0].url} alt={property.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700 ease-out" />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-brand-100 to-brand-200" />
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm px-3 py-1.5 rounded-xl text-sm font-bold text-navy-900 shadow-sm">
                      ${property.base_nightly_rate}<span className="font-normal text-gray-500">/night</span>
                    </div>
                    {property.is_direct_booking_enabled && (
                      <div className="absolute top-4 left-4 bg-accent-500 text-white px-3 py-1 rounded-lg text-xs font-semibold shadow-sm">Save 15%</div>
                    )}
                  </div>
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-navy-900 text-lg leading-tight group-hover:text-accent-600 transition-colors">{property.name}</h3>
                        <p className="text-sm text-gray-500 mt-1 flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {property.city}, {property.state}</p>
                      </div>
                      <div className="flex items-center gap-1 bg-navy-50 px-2 py-1 rounded-lg shrink-0">
                        <Star className="w-3.5 h-3.5 text-accent-500 fill-accent-500" /><span className="text-xs font-semibold text-navy-700">4.9</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500 font-medium">
                      <span>{property.bedrooms} Beds</span><span className="w-1 h-1 bg-gray-300 rounded-full" /><span>{property.bathrooms} Baths</span><span className="w-1 h-1 bg-gray-300 rounded-full" /><span>{property.max_guests} Guests</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
        <div className="text-center mt-10 md:hidden"><Link to="/properties"><Button variant="outline" size="lg">View All Properties</Button></Link></div>
      </section>

      {/* WHY BOOK DIRECT */}
      <section className="bg-navy-950 py-24 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-navy-500/10 rounded-full blur-3xl" />
        <div className="container-page relative z-10">
          <div className="text-center mb-16">
            <p className="text-accent-400 font-semibold text-sm uppercase tracking-widest mb-3">The WiseStay Difference</p>
            <h2 className="text-3xl md:text-5xl font-heading font-bold text-white mb-4">Why Book Direct?</h2>
            <p className="text-gray-400 max-w-lg mx-auto">Skip the middleman. Get better prices, better perks, and a smarter stay.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: Shield, title: 'Save Up to 15%', desc: 'No platform commissions. What you see is the real price — often hundreds less than Airbnb or Booking.com.', highlight: '$340', highlightLabel: 'avg. savings per booking' },
              { icon: Sparkles, title: 'Earn Loyalty Rewards', desc: 'Every dollar earns points. Climb from Bronze to Platinum and unlock exclusive perks like early check-in and late checkout.', highlight: '4 Tiers', highlightLabel: 'of exclusive benefits' },
              { icon: ThermometerSun, title: 'Smart Home Living', desc: 'Keyless entry with personal codes, climate set to your preference, and an AI concierge available 24/7.', highlight: '24/7', highlightLabel: 'AI concierge support' },
            ].map(({ icon: Icon, title, desc, highlight, highlightLabel }, idx) => (
              <div key={title} className="group bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-8 hover:bg-white/10 transition-all duration-300 animate-in" style={{ animationDelay: `${idx * 0.15}s` }}>
                <div className="w-14 h-14 bg-accent-500/20 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-accent-500/30 transition-colors">
                  <Icon className="w-7 h-7 text-accent-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed mb-6">{desc}</p>
                <div className="pt-6 border-t border-white/10">
                  <p className="text-3xl font-heading font-bold text-accent-400">{highlight}</p>
                  <p className="text-xs text-gray-500 mt-1">{highlightLabel}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SMART HOME EXPERIENCE */}
      <section className="py-24 bg-brand-50/50">
        <div className="container-page">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <p className="text-accent-600 font-semibold text-sm uppercase tracking-widest mb-3">Smart Technology</p>
              <h2 className="text-3xl md:text-4xl font-heading font-bold text-navy-900 mb-6">Every Stay is a{' '}<span className="italic text-accent-600">Smart</span> Stay</h2>
              <p className="text-gray-500 leading-relaxed mb-8">Our properties come equipped with the latest IoT technology. From the moment you arrive, everything is automated for your comfort.</p>
              <div className="space-y-5">
                {[
                  { icon: Key, label: 'Keyless Entry', desc: 'Personal door codes generated 48h before check-in' },
                  { icon: ThermometerSun, label: 'Climate Control', desc: 'Temperature set to your preference before arrival' },
                  { icon: Wifi, label: 'Seamless Connectivity', desc: 'High-speed WiFi with credentials in your app' },
                  { icon: MessageCircle, label: 'AI Concierge', desc: 'Ask anything — 24/7 via chat or WhatsApp' },
                ].map(({ icon: Icon, label, desc }) => (
                  <div key={label} className="flex items-start gap-4 group">
                    <div className="w-12 h-12 bg-white rounded-2xl shadow-soft flex items-center justify-center shrink-0 group-hover:shadow-elevated transition-shadow">
                      <Icon className="w-5 h-5 text-accent-600" />
                    </div>
                    <div><h4 className="font-semibold text-navy-900">{label}</h4><p className="text-sm text-gray-500">{desc}</p></div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="aspect-[4/5] rounded-3xl overflow-hidden shadow-elevated">
                <img src="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80" alt="Smart luxury home" className="w-full h-full object-cover" />
              </div>
              <div className="absolute -bottom-6 -left-6 bg-white rounded-2xl shadow-elevated p-5 max-w-[240px] animate-float">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-success-50 rounded-xl flex items-center justify-center"><Key className="w-5 h-5 text-success-500" /></div>
                  <div><p className="text-sm font-semibold text-navy-900">Door Unlocked</p><p className="text-xs text-gray-500">Code: ****91</p></div>
                </div>
                <div className="h-1.5 bg-success-500 rounded-full w-full" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* LOYALTY PROGRAM */}
      <section className="py-24">
        <div className="container-page">
          <div className="relative bg-gradient-to-br from-navy-900 via-navy-950 to-navy-900 rounded-[2rem] overflow-hidden">
            <div className="absolute top-0 right-0 w-80 h-80 bg-accent-500/10 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-1/4 w-64 h-64 bg-accent-400/5 rounded-full blur-2xl" />
            <div className="relative z-10 p-10 md:p-16 text-center">
              <div className="inline-flex items-center gap-2 bg-accent-500/20 text-accent-300 px-4 py-1.5 rounded-full text-sm font-medium mb-6">
                <Sparkles className="w-4 h-4" /> WiseStay Rewards
              </div>
              <h2 className="text-3xl md:text-5xl font-heading font-bold text-white mb-4 max-w-2xl mx-auto">
                Every Stay Brings You{' '}<span className="text-accent-400 italic">Closer</span>
              </h2>
              <p className="text-gray-400 max-w-lg mx-auto mb-10 leading-relaxed">Earn points on every direct booking. Climb tiers from Bronze to Platinum and unlock perks like 15% discounts, early check-in, and priority support.</p>
              <div className="flex items-center justify-center gap-3 md:gap-6 mb-10 flex-wrap">
                {[
                  { name: 'Bronze', color: 'bg-amber-700' },
                  { name: 'Silver', color: 'bg-gray-400' },
                  { name: 'Gold', color: 'bg-accent-500' },
                  { name: 'Platinum', color: 'bg-gray-200' },
                ].map(({ name, color }, idx) => (
                  <div key={name} className="flex items-center gap-3">
                    <div className="text-center">
                      <div className={`w-12 h-12 md:w-14 md:h-14 ${color} rounded-2xl mx-auto mb-2 shadow-lg`} />
                      <p className="text-xs md:text-sm font-semibold text-white">{name}</p>
                    </div>
                    {idx < 3 && <ChevronRight className="w-4 h-4 text-gray-600 hidden md:block" />}
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-center gap-4 flex-wrap">
                <Link to="/loyalty-program"><Button variant="outline" size="lg" className="border-white/20 text-white hover:bg-white/10">Learn More</Button></Link>
                <Link to="/register"><Button size="lg" className="bg-accent-500 hover:bg-accent-600 text-white shadow-glow">Join Free</Button></Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="py-24 bg-brand-50/30">
        <div className="container-page">
          <div className="text-center mb-14">
            <p className="text-accent-600 font-semibold text-sm uppercase tracking-widest mb-2">Guest Reviews</p>
            <h2 className="text-3xl md:text-4xl font-heading font-bold text-navy-900">What Our Guests Say</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { name: 'Sarah M.', location: 'Austin, TX', text: "The smart lock was seamless — no waiting around for keys. And the AI concierge helped us find the best restaurants nearby. We saved over $200 vs. Airbnb!" },
              { name: 'James & Lisa R.', location: 'Miami, FL', text: "We're Gold tier now and the perks are incredible. Early check-in, late checkout, plus the 10% discount makes every trip feel like a steal." },
              { name: 'David K.', location: 'Nashville, TN', text: "The property was exactly as described. Temperature was perfect when we arrived. This is what vacation rental should feel like." },
            ].map(({ name, location, text }) => (
              <div key={name} className="bg-white rounded-3xl p-8 shadow-soft border border-gray-100 card-hover">
                <Quote className="w-8 h-8 text-accent-200 mb-4" />
                <p className="text-gray-600 leading-relaxed mb-6">{text}</p>
                <div className="flex items-center gap-1 mb-4">{Array.from({ length: 5 }).map((_, i) => <Star key={i} className="w-4 h-4 text-accent-500 fill-accent-500" />)}</div>
                <div><p className="font-semibold text-navy-900">{name}</p><p className="text-sm text-gray-500">{location}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CONTACT CTA */}
      <section className="py-20">
        <div className="container-page text-center">
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-navy-900 mb-4">Have Questions?</h2>
          <p className="text-gray-500 mb-8 max-w-md mx-auto">Our AI concierge is available 24/7. Or reach out to our team directly.</p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link to="/chat"><Button size="lg" className="gap-2"><MessageCircle className="w-5 h-5" /> Chat with Concierge</Button></Link>
            <a href="https://wa.me/14155551234" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="lg" className="gap-2 border-green-500 text-green-600 hover:bg-green-50 hover:border-green-600">
                <Phone className="w-5 h-5" /> WhatsApp
              </Button>
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
