import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import Card from '../common/Card';
import Badge from '../common/Badge';
import Spinner from '../common/Spinner';
import {
  DocumentTextIcon,
  ClockIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

const severityConfig = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Critique' },
  high: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Haute' },
  medium: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', label: 'Moyenne' },
  low: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', label: 'Basse' },
  info: { color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', label: 'Info' },
};

// Map service key → backend stored label (from Python's .replace('_',' ').title())
const serviceLabelMap = {
  breach_lookup: 'Breach Lookup',
  social_harvester: 'Social Harvester',
  dns_investigator: 'DNS Investigator',
  ip_geoloc: 'IP Geolocation',
  person_finder: 'Person Finder',
  email_investigator: 'Email Investigator',
  web_scanner: 'Web Scanner',
  wayback_machine: 'Wayback Machine',
  image_search: 'Image Search',
  phone_analyzer: 'Phone Analyzer',
  text_analyzer: 'Text Analyzer',
  url_expander: 'URL Expander',
  shodan_lookup: 'Shodan Lookup',
};

export default function ServiceReports({ serviceName, limit = 5 }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const svcLabel = serviceLabelMap[serviceName] || serviceName;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // Fetch recent reports and filter client-side by service label
    api.get('/reports', {
      params: { limit: 50 },
    })
      .then((res) => {
        if (!cancelled) {
          const allReports = res?.data?.reports || [];
          // Accept reports whose service field starts with or matches the label
          const filtered = allReports.filter(
            (r) => r.service === svcLabel || r.service?.startsWith(svcLabel)
          );
          setReports(filtered.slice(0, limit));
        }
      })
      .catch(() => {
        if (!cancelled) setReports([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [serviceName, limit]);

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-6">
          <Spinner size="sm" />
          <span className="ml-2 text-sm text-gray-500">Chargement des rapports...</span>
        </div>
      </Card>
    );
  }

  if (reports.length === 0) {
    return null;
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <DocumentTextIcon className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Rapports récents
          </h3>
          <Badge severity="default" size="sm">{reports.length}</Badge>
        </div>
      </div>

      <div className="space-y-2">
        {reports.map((report) => {
          const sev = severityConfig[report.severity] || severityConfig.info;
          const date = report.created_at
            ? new Date(report.created_at).toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              })
            : '';
          const score = report.score ?? '—';

          return (
            <button
              key={report.id}
              onClick={() => navigate(`/reports/${report.id}`)}
              className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-gray-800 bg-gray-900/30 hover:bg-gray-800/50 hover:border-gray-700 transition-all text-left group"
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className={`p-1.5 rounded-md ${sev.bg} ${sev.border} border flex-shrink-0`}>
                  <span className={`text-xs font-bold font-mono ${sev.color}`}>{score}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-200 truncate">
                    {report.target}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-gray-500 flex items-center gap-1">
                      <ClockIcon className="w-3 h-3" />
                      {date}
                    </span>
                    <Badge severity={report.severity === 'critical' ? 'critical' : report.severity} size="sm" dot>
                      {sev.label}
                    </Badge>
                  </div>
                </div>
              </div>
              <ChevronRightIcon className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors flex-shrink-0" />
            </button>
          );
        })}
      </div>
    </Card>
  );
}
