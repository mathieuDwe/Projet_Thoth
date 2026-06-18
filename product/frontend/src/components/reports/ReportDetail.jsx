import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useReports from '../../hooks/useReports';
import Card from '../common/Card';
import Badge from '../common/Badge';
import Button from '../common/Button';
import Spinner from '../common/Spinner';
import ReportExport from './ReportExport';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

const severityMap = {
  critical: { severity: 'critical', label: 'Critique' },
  high: { severity: 'high', label: 'Haute' },
  medium: { severity: 'medium', label: 'Moyenne' },
  low: { severity: 'low', label: 'Basse' },
  info: { severity: 'info', label: 'Info' },
};

const serviceIcons = {
  breach_lookup: { color: 'bg-red-500', label: 'Breach Lookup' },
  social_harvester: { color: 'bg-purple-500', label: 'Social Harvester' },
  dns_investigator: { color: 'bg-cyan-500', label: 'DNS Investigator' },
  ip_geoloc: { color: 'bg-amber-500', label: 'IP Geolocation' },
};

export default function ReportDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { reportDetail, loading, error, fetchReport } = useReports();
  const [report, setReport] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    if (reportDetail && reportDetail.id === id) {
      setReport(reportDetail);
    } else {
      fetchReport(id);
    }
  }, [id, reportDetail, fetchReport]);

  // When reportDetail updates from the fetch, set local state
  useEffect(() => {
    if (reportDetail && reportDetail.id === id) {
      setReport(reportDetail);
    }
  }, [reportDetail, id]);

  if (!report && !error) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" text="Chargement du rapport..." />
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/reports')}>
          <ArrowLeftIcon className="w-4 h-4" />
          Retour aux rapports
        </Button>
        <Card>
          <p className="text-red-400 text-center py-8">{error}</p>
        </Card>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/reports')}>
          <ArrowLeftIcon className="w-4 h-4" />
          Retour aux rapports
        </Button>
        <Card>
          <p className="text-gray-400 text-center py-8">Rapport introuvable</p>
        </Card>
      </div>
    );
  }

  const severityInfo = severityMap[report.severity] || severityMap.info;
  const formatDate = (d) =>
    new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });

  // Extract investigation data
  const investigationData = report.data || {};
  const results = investigationData.results || {};
  const resultEntries = Object.entries(results);
  const allTargets = [investigationData.email, investigationData.username, investigationData.domain, investigationData.ip].filter(Boolean);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back + Export */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/reports')}>
          <ArrowLeftIcon className="w-4 h-4" />
          Retour
        </Button>
        <ReportExport reportId={report.id} onExport={async (id, format) => {
          try {
            const { exportReport } = await import('../../services/reports');
            const data = await exportReport(id, format);
            if (format === 'json') {
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `report-${id}.json`;
              a.click();
              URL.revokeObjectURL(url);
            } else if (format === 'pdf' || format === 'markdown') {
              const blob = new Blob([data], { type: format === 'pdf' ? 'application/pdf' : 'text/markdown' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `report-${id}.${format}`;
              a.click();
              URL.revokeObjectURL(url);
            }
          } catch (err) {
            console.error('Export failed:', err);
          }
        }} />
      </div>

      {/* Header Card */}
      <Card>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-100 font-mono">
                {report.target}
              </h1>
              <Badge severity={severityInfo.severity} dot>
                {severityInfo.label}
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>{report.service}</span>
              <span>•</span>
              <span>{formatDate(report.created_at)}</span>
              {report.score !== undefined && report.score !== null && (
                <>
                  <span>•</span>
                  <span className="text-emerald-400 font-mono">Score: {report.score}/10</span>
                </>
              )}
            </div>
            {allTargets.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {allTargets.map((t, i) => (
                  <span key={i} className="px-2 py-0.5 text-[10px] rounded bg-gray-800 text-gray-400 font-mono border border-gray-700/50">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        {report.summary && (
          <p className="mt-4 text-sm text-gray-300 border-t border-gray-800 pt-4 whitespace-pre-wrap">
            {report.summary}
          </p>
        )}
      </Card>

      {/* Microservice Results */}
      {resultEntries.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Résultats détaillés par service
          </h3>
          <div className="space-y-3">
            {resultEntries.map(([svcName, svcData]) => {
              const svcIcon = serviceIcons[svcName] || { color: 'bg-gray-500', label: svcName };
              const isSuccess = svcData?.success;
              const svcLabel = svcName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
              return (
                <div
                  key={svcName}
                  className="rounded-lg bg-gray-800/30 border border-gray-800/50 overflow-hidden"
                >
                  {/* Service Header */}
                  <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800/50 bg-gray-900/30">
                    <span className={`w-2 h-2 rounded-full ${isSuccess ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    <span className="text-sm font-medium text-gray-200">{svcLabel}</span>
                    {!isSuccess && (
                      <span className="text-xs text-red-400 ml-auto">Échec</span>
                    )}
                  </div>
                  {/* Service Content */}
                  <div className="px-4 py-3">
                    {isSuccess ? (
                      <div className="space-y-2">
                        {svcData.summary && (
                          <p className="text-sm text-gray-400">{svcData.summary}</p>
                        )}
                        {svcData.data && Object.keys(svcData.data).length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {Object.entries(svcData.data).map(([key, val]) => (
                              <span key={key} className="px-2 py-1 text-[10px] rounded bg-gray-900 text-gray-400 font-mono border border-gray-700/50">
                                {key}: {typeof val === 'object' ? JSON.stringify(val).slice(0, 60) : String(val).slice(0, 60)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-red-400 font-mono">
                        {svcData.error || 'Service indisponible'}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Raw Data */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Données brutes
          </h3>
          <Button variant="ghost" size="sm" onClick={() => setShowRaw(!showRaw)}>
            {showRaw ? 'Masquer' : 'Afficher'}
          </Button>
        </div>
        {showRaw && (
          <pre className="p-4 rounded-lg bg-gray-950 border border-gray-800 overflow-x-auto text-xs text-emerald-400 font-mono leading-relaxed max-h-96 overflow-y-auto">
            {JSON.stringify(report.data || report, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
