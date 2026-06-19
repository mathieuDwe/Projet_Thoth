import { NavLink, useNavigate } from 'react-router-dom';
import {
  ChartBarIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  Cog6ToothIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  ShieldExclamationIcon,
  GlobeAltIcon,
  UsersIcon,
  MapPinIcon,
  UserGroupIcon,
  EnvelopeIcon,
  CodeBracketIcon,
  ClockIcon,
  MagnifyingGlassCircleIcon,
  PhoneIcon,
  DocumentTextIcon as DocIcon,
  LinkIcon,
  ServerStackIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';

const navigation = [
  { name: 'Dashboard', path: '/', icon: ChartBarIcon },
  { name: 'Enquêtes', path: '/scan', icon: MagnifyingGlassIcon },
  { name: 'Rapports', path: '/reports', icon: DocumentTextIcon },
  { name: 'Paramètres', path: '/settings', icon: Cog6ToothIcon },
];

const services = [
  { name: 'Breach Lookup', path: '/tools/breach-lookup', icon: ShieldExclamationIcon },
  { name: 'DNS Investigator', path: '/tools/dns-investigator', icon: GlobeAltIcon },
  { name: 'Social Harvester', path: '/tools/social-harvester', icon: UsersIcon },
  { name: 'IP Geolocation', path: '/tools/ip-geolocation', icon: MapPinIcon },
  { name: 'Person Finder', path: '/tools/person-finder', icon: UserGroupIcon },
  { name: 'Email Investigator', path: '/tools/email-investigator', icon: EnvelopeIcon },
  { name: 'Web Scanner', path: '/tools/web-scanner', icon: CodeBracketIcon },
  { name: 'Wayback Machine', path: '/tools/wayback-machine', icon: ClockIcon },
  { name: 'Image Search', path: '/tools/image-search', icon: MagnifyingGlassCircleIcon },
  { name: 'Phone Analyzer', path: '/tools/phone-analyzer', icon: PhoneIcon },
  { name: 'Text Analyzer', path: '/tools/text-analyzer', icon: DocIcon },
  { name: 'URL Expander', path: '/tools/url-expander', icon: LinkIcon },
  { name: 'Shodan Lookup', path: '/tools/shodan-lookup', icon: ServerStackIcon },
];

export default function Sidebar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900/95 backdrop-blur-md border-r border-gray-800 flex flex-col z-40">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-800">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
          <span className="text-emerald-400 font-bold text-sm">T</span>
        </div>
        <div>
          <span className="text-sm font-bold text-gray-100 tracking-wider">THOTH</span>
          <span className="block text-[10px] text-gray-500 uppercase tracking-[0.2em]">OSINT Platform</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {item.name}
            </NavLink>
          );
        })}

        {/* Section Services / Outils */}
        <div className="pt-4 pb-1">
          <span className="px-3 text-[10px] font-semibold text-gray-600 uppercase tracking-[0.15em]">
            Services
          </span>
        </div>
        {services.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-200 pl-9 ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 border border-transparent'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {item.name}
            </NavLink>
          );
        })}

        {/* Lien Profil */}
        <div className="pt-2">
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent'
              }`
            }
          >
            <UserCircleIcon className="w-5 h-5 flex-shrink-0" />
            Profil
          </NavLink>
        </div>
      </nav>

      {/* Footer / User Info */}
      <div className="px-4 py-4 border-t border-gray-800 space-y-3">
        {isAuthenticated ? (
          <>
            {/* User info */}
            <div className="flex items-center gap-3 px-2">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                <span className="text-emerald-400 font-bold text-sm uppercase">
                  {user?.username?.charAt(0) || '?'}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-200 truncate">
                  {user?.username || 'Utilisateur'}
                </p>
                <p className="text-[10px] text-gray-500 truncate">
                  {user?.email || ''}
                </p>
              </div>
            </div>

            {/* Logout button */}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
            >
              <ArrowRightOnRectangleIcon className="w-4 h-4" />
              Déconnexion
            </button>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50" />
              <span className="text-xs text-gray-500">Système opérationnel</span>
            </div>
            <NavLink
              to="/login"
              className="block w-full text-center px-3 py-2 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-all"
            >
              Se connecter
            </NavLink>
          </>
        )}
        <span className="block text-[10px] text-gray-600 px-2">Thoth v1.0.0</span>
      </div>
    </aside>
  );
}
