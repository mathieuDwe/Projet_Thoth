import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Card from '../common/Card';
import Button from '../common/Button';
import Badge from '../common/Badge';
import Spinner from '../common/Spinner';
import {
  MagnifyingGlassIcon,
  GlobeAltIcon,
  AtSymbolIcon,
  LinkIcon,
  ServerIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  UserIcon,
  BuildingOfficeIcon,
  EnvelopeIcon,
  IdentificationIcon,
} from '@heroicons/react/24/outline';
import { investigateGlobal } from '../../services/investigation';

// ── Catégories d'enquête ──
const subjectTypes = [
  {
    value: 'person',
    label: 'Personne',
    description: 'Trouver des infos sur une personne (réseaux, breaches)',
    icon: UserIcon,
    placeholder: 'Nom, pseudo ou email...',
    services: ['social', 'breach'],
    payload: (v) => {
      if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return { email: v };
      return { username: v };
    },
  },
  {
    value: 'company',
    label: 'Entreprise',
    description: 'Infos sur une société (domaine, WHOIS, DNS)',
    icon: BuildingOfficeIcon,
    placeholder: 'Nom entreprise ou domaine...',
    services: ['dns', 'ip'],
    payload: (v) => {
      if (/^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/.test(v)) return { domain: v };
      // Si c'est un nom d'entreprise, tenter une recherche domaine
      const domain = v.toLowerCase().replace(/[^a-z0-9]/g, '') + '.com';
      return { domain, company: v };
    },
  },
  {
    value: 'site',
    label: 'Site Web',
    description: 'Analyser un site (DNS, IP, certificats)',
    icon: LinkIcon,
    placeholder: 'https://exemple.com',
    services: ['dns', 'ip'],
    payload: (v) => {
      try {
        const url = new URL(v.startsWith('http') ? v : `https://${v}`);
        return { domain: url.hostname, url: v };
      } catch {
        return { domain: v };
      }
    },
  },
  {
    value: 'ip',
    label: 'Adresse IP',
    description: 'Géolocalisation, FAI, VPN/proxy',
    icon: ServerIcon,
    placeholder: '8.8.8.8',
    services: ['ip'],
    payload: (v) => ({ ip: v }),
  },
  {
    value: 'email',
    label: 'Email',
    description: 'Vérifier un email (breaches, fuites)',
    icon: EnvelopeIcon,
    placeholder: 'email@exemple.com',
    services: ['breach'],
    payload: (v) => ({ email: v }),
  },
  {
    value: 'domain',
    label: 'Domaine',
    description: 'Analyse DNS complète (enregistrements, WHOIS)',
    icon: GlobeAltIcon,
    placeholder: 'exemple.com',
    services: ['dns'],
    payload: (v) => ({ domain: v }),
  },
];

const scanServices = [
  { id: 'breach', label: 'Breach Lookup', icon: GlobeAltIcon, enabled: true },
  { id: 'social', label: 'Social Harvester', icon: AtSymbolIcon, enabled: true },
  { id: 'dns', label: 'DNS Investigator', icon: GlobeAltIcon, enabled: true },
  { id: 'ip', label: 'IP Geolocation', icon: ServerIcon, enabled: true },
  { id: 'cert', label: 'Certificate Search', icon: LinkIcon, enabled: false },
];

const serviceLabelMap = {
  breach_lookup: 'Breach Lookup',
  social_harvester: 'Social Harvester',
  dns_investigator: 'DNS Investigator',
  ip_geoloc: 'IP Geolocation',
};

const subjectToServiceKeys = {
  breach: ['breach_lookup'],
  social: ['social_harvester'],
  dns: ['dns_investigator'],
  ip: ['ip_geoloc'],
};

const severityConfig = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
  high: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
  medium: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
  low: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
  info: { color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20' },
};

export default function ScanForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const prefilledTarget = searchParams.get('target') || '';

  const [target, setTarget] = useState(prefilledTarget);
  const [subjectType, setSubjectType] = useState('domain');
  const [selectedServices, setSelectedServices] = useState([]);
  const [error, setError] = useState('');
  const [isScanning, setIsScanning] = useState(false);

  // Résultat de l'enquête (affiché en place)
  const [result, setResult] = useState(null);

  // Progression en temps réel par service
  const [scanProgress, setScanProgress] = useState({});

  // Sélectionner les services par défaut quand le type de sujet change
  useEffect(() => {
    const subject = subjectTypes.find((s) => s.value === subjectType);
    if (subject) {
      setSelectedServices(subject.services);
    }
  }, [subjectType]);

  // Détection automatique du type de sujet depuis l'URL ?target=
  useEffect(() => {
    if (prefilledTarget) {
      if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(prefilledTarget)) {
        setSubjectType('email');
      } else if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(prefilledTarget)) {
        setSubjectType('ip');
      } else if (/^https?:\/\//.test(prefilledTarget)) {
        setSubjectType('site');
      } else if (/^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/.test(prefilledTarget)) {
        setSubjectType('domain');
      }
    }
  }, [prefilledTarget]);

  const toggleService = (serviceId) => {
    setSelectedServices((prev) =>
      prev.includes(serviceId)
        ? prev.filter((s) => s !== serviceId)
        : [...prev, serviceId]
    );
  };

  const getCurrentSubject = () => {
    return subjectTypes.find((s) => s.value === subjectType) || subjectTypes[0];
  };

  const buildPayload = (trimmed) => {
    const subject = getCurrentSubject();
    return subject.payload(trimmed);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = target.trim();

    if (!trimmed) {
      setError('Veuillez entrer une cible');
      return;
    }
    if (trimmed.length < 2) {
      setError('La cible doit contenir au moins 2 caractères');
      return;
    }
    if (selectedServices.length === 0) {
      setError('Sélectionnez au moins un service');
      return;
    }

    setError('');
    setIsScanning(true);
    setResult(null);

    // Initialiser la progression
    const payload = buildPayload(trimmed);
    const servicesToRun = [];
    if (selectedServices.includes('breach')) servicesToRun.push('breach_lookup');
    if (selectedServices.includes('social')) servicesToRun.push('social_harvester');
    if (selectedServices.includes('dns')) servicesToRun.push('dns_investigator');
    if (selectedServices.includes('ip')) servicesToRun.push('ip_geoloc');

    const initialProgress = {};
    servicesToRun.forEach((svc) => {
      initialProgress[svc] = 'pending';
    });
    setScanProgress(initialProgress);

    // Progression en temps réel simulée
    const progressInterval = setInterval(() => {
      setScanProgress((prev) => {
        const next = { ...prev };
        const pendingServices = Object.keys(next).filter((k) => next[k] === 'pending');
        const runningServices = Object.keys(next).filter((k) => next[k] === 'running');
        if (pendingServices.length > 0 && runningServices.length === 0) {
          next[pendingServices[0]] = 'running';
        }
        return next;
      });
    }, 800);

    try {
      const response = await investigateGlobal(payload);

      clearInterval(progressInterval);

      // Marquer tous les services comme terminés
      const finalProgress = {};
      servicesToRun.forEach((svc) => {
        const svcResult = response?.data?.results?.[svc];
        finalProgress[svc] = svcResult?.success === false ? 'error' : svcResult?.data ? 'success' : 'skipped';
      });
      setScanProgress(finalProgress);

      setResult({
        reportId: response.report_id,
        target: response.data?.target || trimmed,
        severity: response.data?.overall_severity || 'info',
        score: response.data?.overall_score || 0,
        results: response.data?.results || {},
        summary: response.data?.summary || '',
      });
    } catch (err) {
      clearInterval(progressInterval);
      setScanProgress((prev) => {
        const failed = {};
        Object.keys(prev).forEach((k) => { failed[k] = 'error'; });
        return failed;
      });
      setError(err.response?.data?.detail || err.message || "Échec de l'enquête");
    } finally {
      setIsScanning(false);
    }
  };

  const handleNewInvestigation = () => {
    setResult(null);
    setScanProgress({});
    setError('');
    setTarget('');
  };

  const handleViewReport = () => {
    if (result?.reportId) {
      navigate(`/reports/${result.reportId}`);
    }
  };

  // === Affichage des résultats ===
  if (result) {
    const severityStyle = severityConfig[result.severity] || severityConfig.info;
    const resultEntries = Object.entries(result.results || {});
    const successCount = resultEntries.filter(([, v]) => v?.success === true).length;
    const failCount = resultEntries.filter(([, v]) => v?.success === false).length;

    return (
      <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Résultat de l'enquête</h1>
            <p className="text-sm text-gray-500 mt-1">
              Investigation terminée sur <span className="font-mono text-emerald-400">{result.target}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={handleNewInvestigation} icon={ArrowPathIcon}>
              Nouvelle enquête
            </Button>
          </div>
        </div>

        {/* Bandeau récapitulatif */}
        <Card>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${severityStyle.bg} border ${severityStyle.border}`}>
                <span className={`text-2xl font-bold font-mono ${severityStyle.color}`}>
                  {result.score}/10
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <Badge severity={result.severity === 'critical' ? 'critical' : result.severity} dot size="lg">
                    {result.severity === 'critical' ? 'Critique' :
                     result.severity === 'high' ? 'Haute' :
                     result.severity === 'medium' ? 'Moyenne' :
                     result.severity === 'low' ? 'Basse' : 'Info'}
                  </Badge>
                  <span className="text-sm text-gray-400">
                    {successCount} service{successCount > 1 ? 's' : ''} OK
                    {failCount > 0 && (
                      <span className="text-red-400"> · {failCount} échec{failCount > 1 ? 's' : ''}</span>
                    )}
                  </span>
                </div>
                {result.summary && (
                  <p className="text-sm text-gray-500 mt-1 max-w-xl truncate">{result.summary}</p>
                )}
              </div>
            </div>
            <Button
              variant="primary"
              size="lg"
              onClick={handleViewReport}
              icon={DocumentTextIcon}
            >
              Voir le rapport complet
            </Button>
          </div>
        </Card>

        {/* Résultats par service */}
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
            Détail par service
          </h3>
          <div className="space-y-2">
            {resultEntries.map(([svcName, svcData]) => {
              const label = serviceLabelMap[svcName] || svcName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
              const isSuccess = svcData?.success === true;
              const isError = svcData?.success === false;

              return (
                <div
                  key={svcName}
                  className={`flex items-center justify-between px-4 py-3 rounded-lg border ${
                    isSuccess
                      ? 'bg-emerald-500/5 border-emerald-500/10'
                      : isError
                      ? 'bg-red-500/5 border-red-500/10'
                      : 'bg-gray-800/20 border-gray-800/30'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {isSuccess ? (
                      <CheckCircleIcon className="w-5 h-5 text-emerald-400" />
                    ) : isError ? (
                      <XCircleIcon className="w-5 h-5 text-red-400" />
                    ) : (
                      <ClockIcon className="w-5 h-5 text-gray-500" />
                    )}
                    <div>
                      <span className="text-sm font-medium text-gray-200">{label}</span>
                      {isSuccess && svcData.summary && (
                        <p className="text-xs text-gray-500 mt-0.5">{svcData.summary}</p>
                      )}
                      {isError && svcData.error && (
                        <p className="text-xs text-red-400/80 mt-0.5">{svcData.error}</p>
                      )}
                    </div>
                  </div>
                  <Badge
                    severity={isSuccess ? 'success' : isError ? 'error' : 'default'}
                    size="sm"
                  >
                    {isSuccess ? 'Succès' : isError ? 'Échec' : 'Ignoré'}
                  </Badge>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Boutons d'action */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={handleNewInvestigation} icon={ArrowPathIcon}>
            Lancer une nouvelle enquête
          </Button>
          <Button
            variant="primary"
            size="lg"
            onClick={handleViewReport}
            icon={DocumentTextIcon}
          >
            Voir le rapport complet
          </Button>
        </div>
      </div>
    );
  }

  // === Affichage du formulaire ===
  const currentSubject = getCurrentSubject();
  const SubjectIcon = currentSubject.icon;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-100">Nouvelle enquête</h1>
        <p className="text-sm text-gray-500 mt-1">
          Choisissez le sujet de votre investigation OSINT
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Sujet de l'enquête */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <MagnifyingGlassIcon className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Sujet de l'enquête
            </h3>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {subjectTypes.map((subject) => {
              const Icon = subject.icon;
              const isActive = subjectType === subject.value;
              return (
                <button
                  key={subject.value}
                  type="button"
                  onClick={() => setSubjectType(subject.value)}
                  className={`
                    flex flex-col items-center gap-1.5 px-3 py-3 rounded-lg border transition-all text-center
                    ${isActive
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                      : 'border-gray-800 bg-gray-900/50 text-gray-400 hover:border-gray-700 hover:text-gray-300'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="text-[11px] font-medium leading-tight">{subject.label}</span>
                </button>
              );
            })}
          </div>

          {currentSubject.description && (
            <p className="mt-3 text-xs text-gray-500 flex items-center gap-1.5">
              <IdentificationIcon className="w-3.5 h-3.5 text-gray-600" />
              {currentSubject.description}
            </p>
          )}
        </Card>

        {/* Cible */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <SubjectIcon className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Cible
            </h3>
          </div>

          <div>
            <div className="relative">
              <input
                type="text"
                value={target}
                onChange={(e) => {
                  setTarget(e.target.value);
                  if (error) setError('');
                }}
                placeholder={currentSubject.placeholder}
                className="input-soc pr-24 text-base"
                autoComplete="off"
                spellCheck={false}
                autoFocus
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-gray-600 font-mono">
                {currentSubject.label.toUpperCase()}
              </span>
            </div>
            {error && (
              <p className="mt-1.5 text-xs text-red-400">{error}</p>
            )}
          </div>
        </Card>

        {/* Services sélectionnés automatiquement */}
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <ServerIcon className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
              Services activés
            </h3>
            <Badge severity="info" size="sm">
              {selectedServices.length}
            </Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {scanServices.map((service) => {
              const Icon = service.icon;
              const isSelected = selectedServices.includes(service.id);
              const isAuto = currentSubject.services.includes(service.id);

              return (
                <button
                  key={service.id}
                  type="button"
                  disabled={!service.enabled}
                  onClick={() => service.enabled && toggleService(service.id)}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left
                    ${
                      !service.enabled
                        ? 'border-gray-800/30 bg-gray-900/30 opacity-40 cursor-not-allowed'
                        : isSelected
                        ? 'border-emerald-500/30 bg-emerald-500/5 text-gray-200'
                        : 'border-gray-800 bg-gray-900/50 text-gray-400 hover:border-gray-700 hover:text-gray-300'
                    }
                  `}
                >
                  <Icon className={`w-5 h-5 ${isSelected ? 'text-emerald-400' : 'text-gray-500'}`} />
                  <div className="flex-1 text-left">
                    <span className="block text-sm font-medium">{service.label}</span>
                    {isAuto && isSelected && (
                      <span className="text-[10px] text-emerald-500/70">Recommandé</span>
                    )}
                  </div>
                  {!service.enabled && (
                    <Badge severity="default" size="sm">Bientôt</Badge>
                  )}
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  )}
                </button>
              );
            })}
          </div>
        </Card>

        {/* Lancement */}
        <div className="flex items-center justify-end gap-3">
          <Button
            variant="ghost"
            type="button"
            onClick={() => navigate('/')}
          >
            Annuler
          </Button>
          <Button
            type="submit"
            size="lg"
            loading={isScanning}
            icon={isScanning ? undefined : ChevronRightIcon}
          >
            {isScanning ? 'Analyse en cours...' : "Lancer l'enquête"}
          </Button>
        </div>
      </form>

      {/* Scanning overlay avec progression temps réel */}
      {isScanning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg mx-4">
            <Card>
              <div className="text-center space-y-4">
                <Spinner size="lg" />
                <div>
                  <p className="text-lg font-semibold text-gray-100">Investigation en cours</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Analyse de <span className="font-mono text-emerald-400">{target}</span>
                  </p>
                </div>

                {/* Progression en temps réel */}
                <div className="space-y-2 mt-4 text-left">
                  {Object.entries(scanProgress).map(([svc, status]) => {
                    const label = serviceLabelMap[svc] || svc.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    return (
                      <div
                        key={svc}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg border ${
                          status === 'success' ? 'bg-emerald-500/10 border-emerald-500/20' :
                          status === 'error' ? 'bg-red-500/10 border-red-500/20' :
                          status === 'running' ? 'bg-cyan-500/10 border-cyan-500/20' :
                          'bg-gray-800/30 border-gray-800/50'
                        }`}
                      >
                        <span className="text-sm text-gray-300">{label}</span>
                        <span className="text-xs font-mono">
                          {status === 'success' && <span className="text-emerald-400">✅ OK</span>}
                          {status === 'error' && <span className="text-red-400">❌ Échec</span>}
                          {status === 'running' && <span className="text-cyan-400 animate-pulse">En cours...</span>}
                          {status === 'pending' && <span className="text-gray-500">En attente</span>}
                          {status === 'skipped' && <span className="text-gray-500">—</span>}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
