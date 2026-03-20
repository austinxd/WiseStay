import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-white font-heading font-bold text-lg mb-4">WiseStay</h3>
            <p className="text-sm text-gray-400">Premium vacation rentals with smart home technology and loyalty rewards.</p>
          </div>
          <div>
            <h4 className="text-white font-medium mb-3">For Guests</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/properties" className="hover:text-white">Browse Properties</Link></li>
              <li><Link to="/loyalty-program" className="hover:text-white">Loyalty Program</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-medium mb-3">For Owners</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/register" className="hover:text-white">List Your Property</Link></li>
              <li><Link to="/login" className="hover:text-white">Owner Login</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-medium mb-3">Legal</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="#" className="hover:text-white">Terms of Service</a></li>
              <li><a href="#" className="hover:text-white">Privacy Policy</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 mt-8 pt-8 text-sm text-center text-gray-500">
          &copy; {new Date().getFullYear()} WiseStay. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
