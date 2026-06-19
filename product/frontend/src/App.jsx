import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './components/dashboard/Dashboard';
import ReportsList from './components/reports/ReportsList';
import ReportDetail from './components/reports/ReportDetail';
import ScanForm from './components/scan/ScanForm';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import BreachLookup from './pages/tools/BreachLookup';
import DNSInvestigator from './pages/tools/DNSInvestigator';
import SocialHarvester from './pages/tools/SocialHarvester';
import IPGeoloc from './pages/tools/IPGeoloc';
import PersonFinder from './pages/tools/PersonFinder';
import EmailInvestigator from './pages/tools/EmailInvestigator';
import WebScanner from './pages/tools/WebScanner';
import WaybackMachine from './pages/tools/WaybackMachine';
import ImageSearch from './pages/tools/ImageSearch';
import PhoneAnalyzer from './pages/tools/PhoneAnalyzer';
import TextAnalyzer from './pages/tools/TextAnalyzer';
import UrlExpander from './pages/tools/UrlExpander';
import ShodanLookup from './pages/tools/ShodanLookup';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Pages publiques (hors layout) */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Pages protégées (avec layout) */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/reports" element={<ReportsList />} />
          <Route path="/reports/:id" element={<ReportDetail />} />
          <Route path="/scan" element={<ScanForm />} />
          <Route path="/tools/breach-lookup" element={<BreachLookup />} />
          <Route path="/tools/dns-investigator" element={<DNSInvestigator />} />
          <Route path="/tools/social-harvester" element={<SocialHarvester />} />
          <Route path="/tools/ip-geolocation" element={<IPGeoloc />} />
          <Route path="/tools/person-finder" element={<PersonFinder />} />
          <Route path="/tools/email-investigator" element={<EmailInvestigator />} />
          <Route path="/tools/web-scanner" element={<WebScanner />} />
          <Route path="/tools/wayback-machine" element={<WaybackMachine />} />
          <Route path="/tools/image-search" element={<ImageSearch />} />
          <Route path="/tools/phone-analyzer" element={<PhoneAnalyzer />} />
          <Route path="/tools/text-analyzer" element={<TextAnalyzer />} />
          <Route path="/tools/url-expander" element={<UrlExpander />} />
          <Route path="/tools/shodan-lookup" element={<ShodanLookup />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

        {/* Redirection par défaut */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
