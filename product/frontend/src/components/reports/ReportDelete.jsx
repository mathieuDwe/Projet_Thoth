import Modal from '../common/Modal';
import Button from '../common/Button';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export default function ReportDelete({ report, onConfirm, onCancel }) {
  if (!report) return null;

  return (
    <Modal
      isOpen={!!report}
      onClose={onCancel}
      title="Confirmer la suppression"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onCancel}>
            Annuler
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            Supprimer
          </Button>
        </>
      }
    >
      <div className="flex flex-col items-center text-center py-4">
        <div className="p-3 rounded-full bg-red-500/10 border border-red-500/20 mb-4">
          <ExclamationTriangleIcon className="w-6 h-6 text-red-400" />
        </div>
        <p className="text-sm text-gray-300">
          Êtes-vous sûr de vouloir supprimer le rapport
        </p>
        <p className="text-sm font-mono text-emerald-400 mt-2">
          {report.target}
        </p>
        <p className="text-xs text-gray-500 mt-3">
          Cette action est irréversible.
        </p>
      </div>
    </Modal>
  );
}
