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
          <Route path="/settings" element={<Settings />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

        {/* Redirection par défaut */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
