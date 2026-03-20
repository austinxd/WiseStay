import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useProperty } from '@/hooks/useProperties';
import { useCalculatePrice, useCreateBooking } from '@/hooks/useBooking';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { MapPin, Users, BedDouble, Bath, Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';

export function PropertyDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: property, isLoading } = useProperty(slug || '');
  const { isAuthenticated, user } = useAuthStore();
  const calculatePrice = useCalculatePrice();
  const createBooking = useCreateBooking();

  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState(2);
  const [imgIdx, setImgIdx] = useState(0);
  const [pointsToRedeem, setPointsToRedeem] = useState(0);

  if (isLoading) return <PageSpinner />;
  if (!property) return <div className="container-page py-16 text-center">Property not found</div>;

  const images = property.images || [];

  const handleCalculate = () => {
    if (!checkIn || !checkOut) { toast.error('Select dates first'); return; }
    calculatePrice.mutate({ property_id: property.id, check_in: checkIn, check_out: checkOut, points_to_redeem: pointsToRedeem });
  };

  const handleBook = async () => {
    if (!isAuthenticated) { window.location.href = `/login?next=/properties/${slug}`; return; }
    if (!checkIn || !checkOut) { toast.error('Select dates'); return; }
    try {
      const result = await createBooking.mutateAsync({ property_id: property.id, check_in: checkIn, check_out: checkOut, guests_count: guests, points_to_redeem: pointsToRedeem });
      toast.success(`Booking created! Code: ${result.confirmation_code}`);
      // In production: redirect to Stripe payment with result.stripe_client_secret
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Booking failed');
    }
  };

  const pricing = calculatePrice.data;

  return (
    <div className="container-page py-8">
      {/* Gallery */}
      <div className="relative rounded-2xl overflow-hidden bg-gray-100 mb-8">
        {images.length > 0 ? (
          <div className="aspect-[16/9] md:aspect-[2/1]">
            <img src={images[imgIdx]?.url} alt={images[imgIdx]?.caption || property.name} className="w-full h-full object-cover" />
            {images.length > 1 && (
              <>
                <button onClick={() => setImgIdx(i => (i - 1 + images.length) % images.length)} className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/80 p-2 rounded-full shadow hover:bg-white"><ChevronLeft className="w-5 h-5" /></button>
                <button onClick={() => setImgIdx(i => (i + 1) % images.length)} className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/80 p-2 rounded-full shadow hover:bg-white"><ChevronRight className="w-5 h-5" /></button>
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/50 text-white px-3 py-1 rounded-full text-sm">{imgIdx + 1} / {images.length}</div>
              </>
            )}
          </div>
        ) : (
          <div className="aspect-[16/9] md:aspect-[2/1] flex items-center justify-center text-gray-400">No images</div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          <div>
            <h1 className="text-3xl font-heading font-bold mb-2">{property.name}</h1>
            <div className="flex items-center gap-2 text-gray-500">
              <MapPin className="w-4 h-4" /><span>{property.city}, {property.state}</span>
            </div>
            <div className="flex items-center gap-4 mt-3 text-sm text-gray-600">
              <span className="flex items-center gap-1"><BedDouble className="w-4 h-4" /> {property.bedrooms} BR</span>
              <span className="flex items-center gap-1"><Bath className="w-4 h-4" /> {property.bathrooms} BA</span>
              <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {property.max_guests} guests</span>
            </div>
          </div>

          {property.description && (
            <div>
              <h2 className="text-xl font-semibold mb-3">About This Property</h2>
              <p className="text-gray-600 leading-relaxed">{property.description}</p>
            </div>
          )}

          {property.amenities?.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Amenities</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {property.amenities.map(a => (
                  <div key={a.id} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">{a.name}</div>
                ))}
              </div>
            </div>
          )}

          <div>
            <h2 className="text-xl font-semibold mb-3">House Rules</h2>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>Check-in: {property.check_in_time}</li>
              <li>Check-out: {property.check_out_time}</li>
              <li>Minimum stay: {property.min_nights} nights</li>
            </ul>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-3">Location</h2>
            <p className="text-gray-600">{property.address}, {property.city}, {property.state} {property.zip_code}</p>
          </div>

          <div className="bg-wisestay-50 rounded-xl p-6 text-center">
            <p className="font-medium text-wisestay-800 mb-2">Questions? Chat with our AI Concierge</p>
            <Link to="/chat"><Button>Start Chat</Button></Link>
          </div>
        </div>

        {/* Booking Widget */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-6 sticky top-24 space-y-4">
            <p className="text-2xl font-bold">${property.base_nightly_rate}<span className="text-gray-400 font-normal text-base"> /night</span></p>

            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium text-gray-500">CHECK-IN</label><input type="date" value={checkIn} onChange={e => { setCheckIn(e.target.value); if (checkOut) handleCalculate(); }} className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" /></div>
              <div><label className="text-xs font-medium text-gray-500">CHECK-OUT</label><input type="date" value={checkOut} onChange={e => { setCheckOut(e.target.value); if (checkIn) handleCalculate(); }} className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" /></div>
            </div>
            <div><label className="text-xs font-medium text-gray-500">GUESTS</label><input type="number" min="1" max={property.max_guests} value={guests} onChange={e => setGuests(+e.target.value)} className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" /></div>

            {checkIn && checkOut && <Button variant="outline" className="w-full" onClick={handleCalculate} loading={calculatePrice.isPending}>Calculate Price</Button>}

            {pricing && (
              <div className="border-t pt-4 space-y-2 text-sm">
                <div className="flex justify-between"><span>${pricing.nightly_rate} x {pricing.nights} nights</span><span>${pricing.subtotal}</span></div>
                <div className="flex justify-between"><span>Cleaning fee</span><span>${pricing.cleaning_fee}</span></div>
                <div className="flex justify-between"><span>Service fee</span><span>${pricing.service_fee}</span></div>
                {pricing.tier_discount && <div className="flex justify-between text-green-600"><span>{pricing.tier_discount.tier_name} discount (-{pricing.tier_discount.percent}%)</span><span>-${pricing.tier_discount.amount}</span></div>}
                {pricing.loyalty && pricing.loyalty.max_redeemable > 0 && (
                  <div className="bg-accent-500/10 rounded-lg p-3 mt-2">
                    <p className="text-xs font-medium text-accent-600 mb-1">{pricing.loyalty.max_redeemable} points available (up to ${pricing.loyalty.max_discount} off)</p>
                    <input type="range" min="0" max={pricing.loyalty.max_redeemable} value={pointsToRedeem} onChange={e => setPointsToRedeem(+e.target.value)} className="w-full" />
                    <p className="text-xs text-gray-500 mt-1">Redeem {pointsToRedeem} points (-${pointsToRedeem})</p>
                  </div>
                )}
                <div className="flex justify-between font-bold text-base border-t pt-2">
                  <span>Total</span>
                  <span>${pricing.charge_amount || pricing.total_before_points}</span>
                </div>
              </div>
            )}

            <Button className="w-full" size="lg" onClick={handleBook} loading={createBooking.isPending}>
              {isAuthenticated ? 'Book Now' : 'Sign in to Book'}
            </Button>
            {!isAuthenticated && <p className="text-xs text-center text-gray-500">Sign in to unlock loyalty discounts</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
