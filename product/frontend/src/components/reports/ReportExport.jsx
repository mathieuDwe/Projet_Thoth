import { useState, useCallback } from 'react';
import Button from '../common/Button';
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  DocumentArrowDownIcon,
} from '@heroicons/react/24/outline';

const exportFormats = [
  { id: 'json', label: 'JSON', icon: CodeBracketIcon, desc: 'Données structurées' },
  { id: 'markdown', label: 'Markdown', icon: DocumentTextIcon, desc: 'Rapport formaté' },
  { id: 'pdf', label: 'PDF', icon: DocumentArrowDownIcon, desc: 'Document portable' },
];

export default function ReportExport({ reportId, onExport }) {
  const [isOpen, setIsOpen] = useState(false);
  const [exporting, setExporting] = useState(null);

  const handleExport = useCallback(
    async (format) => {
      setExporting(format);
      try {
        if (onExport) {
          await onExport(reportId, format);
        } else {
          // Fallback: simulate export
          await new Promise((r) => setTimeout(r, 800));
          // Trigger download simulation
          const blob = new Blob([`Export ${format} du rapport ${reportId}`], {
            type: 'text/plain',
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `report-${reportId}.${format}`;
          a.click();
          URL.revokeObjectURL(url);
        }
      } catch (err) {
        console.error('Export failed:', err);
      } finally {
        setExporting(null);
        setIsOpen(false);
      }
    },
    [reportId, onExport]
  );

  return (
    <div className="relative">
      <Button
        variant="secondary"
        size="md"
        onClick={() => setIsOpen(!isOpen)}
        icon={ArrowDownTrayIcon}
      >
        Exporter
      </Button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-56 z-40 bg-gray-900 border border-gray-800 rounded-xl shadow-xl shadow-black/30 animate-fade-in">
            <div className="p-2 space-y-1">
              <span className="block px-3 py-1.5 text-[10px] text-gray-500 uppercase tracking-wider font-medium">
                Format d'export
              </span>
              {exportFormats.map((fmt) => {
                const Icon = fmt.icon;
                return (
                  <button
                    key={fmt.id}
                    onClick={() => handleExport(fmt.id)}
                    disabled={exporting === fmt.id}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-gray-100 hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Icon className="w-4 h-4 text-gray-500" />
                    <div className="text-left">
                      <span className="block text-sm">{fmt.label}</span>
                      <span className="block text-[10px] text-gray-600">{fmt.desc}</span>
                    </div>
                    {exporting === fmt.id && (
                      <svg className="animate-spin w-4 h-4 ml-auto text-emerald-400" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
