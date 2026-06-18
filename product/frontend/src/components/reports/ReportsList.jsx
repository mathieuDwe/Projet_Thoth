import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useReports from '../../hooks/useReports';
import Card from '../common/Card';
import Badge from '../common/Badge';
import Button from '../common/Button';
import Spinner from '../common/Spinner';
import ReportDelete from './ReportDelete';
import { EyeIcon, TrashIcon } from '@heroicons/react/24/outline';

const severityMap = {
  critical: { severity: 'critical', label: 'Critique' },
  high: { severity: 'high', label: 'Haute' },
  medium: { severity: 'medium', label: 'Moyenne' },
  moderate: { severity: 'moderate', label: 'Modérée' },
  low: { severity: 'low', label: 'Basse' },
  info: { severity: 'info', label: 'Info' },
};

export default function ReportsList() {
  const navigate = useNavigate();
  const { reports, loading, error, fetchReports, removeReport } = useReports();

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    const success = await removeReport(deleteTarget.id);
    setDeleteTarget(null);
  }, [deleteTarget, removeReport]);

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Rapports</h1>
        <p className="text-sm text-gray-500 mt-1">
          Historique des investigations et analyses
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <Card>
          <div className="flex items-center justify-center py-12">
            <Spinner text="Chargement des rapports..." />
          </div>
        </Card>
      ) : reports.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <span className="text-4xl mb-3 opacity-30">📄</span>
            <p className="text-gray-400 text-sm">Aucun rapport trouvé</p>
            <p className="text-gray-600 text-xs mt-1">Lancez une enquête depuis le Dashboard</p>
          </div>
        </Card>
      ) : (
        <Card padding={false}>
          <div className="overflow-x-auto">
            <table className="table-soc">
              <thead>
                <tr>
                  <th>Cible</th>
                  <th>Date</th>
                  <th>Service</th>
                  <th>Sévérité</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => {
                  const severityInfo = severityMap[report.severity] || severityMap.info;
                  return (
                    <tr
                      key={report.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/reports/${report.id}`)}
                    >
                      <td>
                        <span className="font-mono text-emerald-400 text-sm">
                          {report.target}
                        </span>
                      </td>
                      <td className="text-gray-400 text-xs whitespace-nowrap">
                        {formatDate(report.created_at || report.updated_at)}
                      </td>
                      <td>
                        <Badge severity="info" size="sm">
                          {report.service}
                        </Badge>
                      </td>
                      <td>
                        <Badge severity={severityInfo.severity} dot size="sm">
                          {severityInfo.label}
                        </Badge>
                      </td>
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/reports/${report.id}`);
                            }}
                          >
                            <EyeIcon className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteTarget(report);
                            }}
                          >
                            <TrashIcon className="w-4 h-4 text-red-400" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Delete Modal */}
      <ReportDelete
        report={deleteTarget}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
