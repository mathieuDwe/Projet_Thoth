import { useState, useCallback } from 'react';
import { getReports, getReport, deleteReport, exportReport } from '../services/reports';

export default function useReports() {
  const [reports, setReports] = useState([]);
  const [reportDetail, setReportDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReports = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getReports(params);
      // L'API retourne {success, total, offset, limit, reports: [...]}
      setReports(Array.isArray(data) ? data : data?.reports || []);
    } catch (err) {
      setError(err.message);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchReport = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getReport(id);
      // L'API retourne {success, report: {...}}, on extrait le report
      const report = data?.report || data;
      setReportDetail(report);
      return report;
    } catch (err) {
      setError(err.message);
      setReportDetail(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const removeReport = useCallback(async (id) => {
    try {
      await deleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  const handleExport = useCallback(async (id, format) => {
    try {
      const data = await exportReport(id, format);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, []);

  return {
    reports,
    reportDetail,
    loading,
    error,
    fetchReports,
    fetchReport,
    removeReport,
    handleExport,
  };
}
