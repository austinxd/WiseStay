import { Link } from 'react-router-dom';
import { Sparkles, MapPin, Mail, Phone } from 'lucide-react';

export function Footer() {
  return (
    <footer className="bg-navy-950 text-gray-300">
      {/* CTA Banner */}
      <div className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <h2 className="text-3xl font-heading font-bold text-white mb-3">Ready for Your Next Escape?</h2>
          <p className="text-gray-400 mb-6 max-w-md mx-auto">Join WiseStay and start earning rewards on every stay.</p>
          <Link to="/register" className="inline-flex items-center gap-2 bg-accent-500 hover:bg-accent-600 text-white font-semibold px-8 py-3 rounded-xl transition-colors">
            Get Started Free
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-accent-500 rounded-lg flex items-center justify-center"><Sparkles className="w-4 h-4 text-white" /></div>
              <span className="text-lg font-heading font-bold text-white">WiseStay</span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed">Premium vacation rentals with smart home technology and loyalty rewards.</p>
          </div>
          <div>
            <h4 className="text-white font-semibold text-sm uppercase tracking-wider mb-4">Explore</h4>
            <ul className="space-y-3 text-sm">
              <li><Link to="/properties" className="text-gray-400 hover:text-accent-400 transition-colors">All Properties</Link></li>
              <li><Link to="/loyalty-program" className="text-gray-400 hover:text-accent-400 transition-colors">Rewards Program</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold text-sm uppercase tracking-wider mb-4">Company</h4>
            <ul className="space-y-3 text-sm">
              <li><Link to="/register" className="text-gray-400 hover:text-accent-400 transition-colors">List Your Property</Link></li>
              <li><a href="#" className="text-gray-400 hover:text-accent-400 transition-colors">About Us</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold text-sm uppercase tracking-wider mb-4">Legal</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="text-gray-400 hover:text-accent-400 transition-colors">Terms of Service</a></li>
              <li><a href="#" className="text-gray-400 hover:text-accent-400 transition-colors">Privacy Policy</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 mt-12 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-gray-600">&copy; {new Date().getFullYear()} WiseStay, Inc. All rights reserved.</p>
          <div className="flex items-center gap-6 text-sm text-gray-500">
            <a href="#" className="hover:text-gray-300">Twitter</a>
            <a href="#" className="hover:text-gray-300">Instagram</a>
            <a href="#" className="hover:text-gray-300">LinkedIn</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
