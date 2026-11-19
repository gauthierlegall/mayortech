import React, { useState, useEffect } from 'react';
import {
  Inbox,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  HardHat,
  Calendar,
  Sparkles,
  Plus,
  UserCheck,
  FileText,
  Building2,
  MapPin,
  Eye,
  SlidersHorizontal,
  ChevronRight,
  ShieldCheck,
  Check,
  RotateCcw,
  Maximize2,
  Sun,
  Coins,
  Heart
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useWorkspace } from './context';
import { useOrganizationModules } from './organization-modules-context';
import { INITIAL_DOSSIERS, ValidationDossier } from '../workflow/validation/validationData';
import { MayorValidationLaunchModal } from '../workflow/validation/MayorValidationLaunchModal';
import { AbsenceDelegationModal } from './AbsenceDelegationModal';
import { getCommissionConfig } from './commissionConfig';

function getDocumentSummary(d: ValidationDossier): string {
  if (d.id.startsWith('ARR')) return `${d.documents.length} pièces d'instruction technique et projet d'arrêté`;
  if (d.id.startsWith('MP')) return `${d.documents.length} pièces : CCTP, acte d'engagement & rapport CAO`;
  if (d.id.startsWith('CCAS')) return `${d.documents.length} pièces : rapport social et pièces justificatives (L.226-13)`;
  if (d.id.startsWith('DELIB')) return `${d.documents.length} pièces : projet de délibération et exposé des motifs`;
  if (d.id.startsWith('SUBV')) return `${d.documents.length} pièces : convention d'objectifs et bilan financier`;
  return `${d.documents.length} pièces d'instruction et plans`;
}

export function TodayDashboardView() {
  const { session, state, activeCommissionId } = useWorkspace();
  const { hasModule, organization } = useOrganizationModules();
  const commissionCfg = getCommissionConfig(activeCommissionId);

  const [dossiers, setDossiers] = useState<ValidationDossier[]>(INITIAL_DOSSIERS);
  const [isEluFocusMode, setIsEluFocusMode] = useState<boolean>(() => {
    return localStorage.getItem('mayortech_focus_elu_mode') === 'true';
  });

  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);
  const [isDelegationOpen, setIsDelegationOpen] = useState(false);
  const [activeEluTab, setActiveEluTab] = useState<'signatures' | 'agenda' | 'dossiers'>('signatures');

  const toggleFocusMode = () => {
    const next = !isEluFocusMode;
    setIsEluFocusMode(next);
    localStorage.setItem('mayortech_focus_elu_mode', String(next));
    window.dispatchEvent(new CustomEvent('mayortech:focus-elu-changed', { detail: { active: next } }));
    toast.info(next ? 'Mode Focus Élu activé (zéro distraction)' : 'Mode standard complet réactivé');
  };

  useEffect(() => {
    const handler = (e: Event) => {
      if (e instanceof CustomEvent && typeof e.detail?.active === 'boolean') {
        setIsEluFocusMode(e.detail.active);
      }
    };
    window.addEventListener('mayortech:focus-elu-changed', handler);
    return () => window.removeEventListener('mayortech:focus-elu-changed', handler);
  }, []);

  const allowedDossiers = dossiers.filter((d) => commissionCfg.allowedDossierIds.includes(d.id));
  const pendingDossiers = allowedDossiers.filter((d) => d.status === 'pending');
  const urgentCount = allowedDossiers.filter((d) => d.slaStatus === 'warning').length;
  const activeProjectsCount = state.projects.filter((p) => p.status === 'En cours').length || 2;

  // Format today's date in french
  const todayFormatted = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date());
  const capitalizedDate = todayFormatted.charAt(0).toUpperCase() + todayFormatted.slice(1);

  // Quick sign in focus mode
  const handleQuickSign = (dossierId: string) => {
    setDossiers((prev) =>
      prev.map((d) =>
        d.id === dossierId
          ? { ...d, status: 'signed', currentStepIndex: d.steps.length - 1 }
          : d
      )
    );
    toast.success(`Dossier ${dossierId} visé et signé avec succès.`);
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-5 font-sans text-stone-900 pb-28 sm:pb-12">
      {/* 1. Contextual Welcome Banner */}
      <div className="bg-white border border-stone-200/90 rounded-2xl p-5 sm:p-6 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#102A4C] uppercase tracking-wider">
              <Sun className="w-3.5 h-3.5 text-amber-500" />
              <span>{commissionCfg.roleTitle} · {organization?.name || 'Ville de Plougastel-Daoulas'}</span>
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-stone-900 tracking-tight">
                Bonjour {commissionCfg.greetingName}
              </h1>
              <p className="text-sm text-stone-500">{capitalizedDate}</p>
            </div>
          </div>
        </div>

        {/* 3 Clickable KPI Stat Pills */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          {commissionCfg.kpis.map((kpi) => (
            <a
              key={kpi.id}
              href={kpi.filterId ? `#/workflows` : kpi.id === 'kpi-3' && commissionCfg.hasChantiers ? '#/dossiers' : '#/workflows'}
              className="flex items-center justify-between p-3.5 rounded-xl bg-white hover:bg-stone-50 border border-stone-200/90 transition-colors group cursor-pointer shadow-3xs"
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm shadow-2xs tabular-nums text-white"
                  style={{
                    backgroundColor:
                      kpi.color === 'blue'
                        ? '#102A4C'
                        : kpi.color === 'amber'
                        ? '#B45309'
                        : kpi.color === 'rose'
                        ? '#9F1239'
                        : kpi.color === 'emerald'
                        ? '#0F766E'
                        : '#6D28D9'
                  }}
                >
                  {kpi.count}
                </div>
                <div>
                  <p className="text-xs font-bold text-stone-900">{kpi.title}</p>
                  <p className="text-[11px] text-stone-500">{kpi.subtitle}</p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-stone-400 group-hover:translate-x-0.5 transition-transform" />
            </a>
          ))}
        </div>
      </div>

      {/* Focus Mode Simplified View Banner (if activated) */}
      {isEluFocusMode ? (
        <div className="bg-white border-2 border-[#102A4C]/30 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-stone-200">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#102A4C] bg-stone-100 border border-stone-200 px-2 py-0.5 rounded">
                Vue Simplifiée Élu · Zéro distraction
              </span>
              <h2 className="text-lg font-bold text-stone-900 mt-1">
                Vos signatures prioritaires du jour ({pendingDossiers.length})
              </h2>
            </div>
          </div>

          <div className="space-y-4">
            {pendingDossiers.map((d) => (
              <div
                key={d.id}
                className="p-5 rounded-2xl border border-stone-200 bg-[#FFFEFC] hover:border-[#102A4C]/40 hover:shadow-xs transition-all space-y-3"
              >
                <div className="filet-tricolore" />
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-2 py-0.5 rounded">
                      {d.id}
                    </span>
                    <span className="text-sm font-bold text-stone-900">{d.title}</span>
                    <span className="text-xs text-stone-400">·</span>
                    <span className="text-xs text-stone-600 font-medium">{d.applicant}</span>
                  </div>

                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded-full inline-flex items-center gap-1.5 border self-start sm:self-auto ${
                      d.slaStatus === 'warning'
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-stone-100 text-stone-800 border-stone-200'
                    }`}
                  >
                    <Clock className="w-3 h-3" />
                    <span>{d.slaDeadline}</span>
                  </span>
                </div>

                <p className="text-xs text-stone-700 italic bg-white p-3 rounded-xl border border-stone-200 font-serif-act line-clamp-2">
                  {d.previewArticle}
                </p>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-stone-500 font-medium">
                    Pièces justificatives : {getDocumentSummary(d)}
                  </span>
                  <div className="flex items-center gap-2">
                    <a
                      href={`#/workflows?dossier=${d.id}`}
                      className="px-3.5 py-1.5 rounded-md border border-stone-200 text-stone-700 hover:bg-stone-50 text-xs font-semibold"
                    >
                      Voir le dossier complet
                    </a>
                    <button
                      onClick={() => handleQuickSign(d.id)}
                      className="px-4 py-1.5 rounded-md bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs font-bold shadow-xs flex items-center gap-1.5 cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Viser & Signer</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* 2-Column Responsive Layout */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Main Column (65% / 8 cols) — Priorités à traiter maintenant */}
          <div className="lg:col-span-8 space-y-5">
            {/* Priorités à traiter */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                <div className="flex items-center gap-2">
                  <Inbox className="w-4 h-4 text-[#102A4C]" />
                  <h2 className="text-sm font-bold text-stone-900 tracking-tight">
                    Priorités à traiter maintenant
                  </h2>
                  <span className="text-[10px] font-bold bg-stone-100 text-stone-800 px-1.5 py-0.5 rounded-full font-mono tabular-nums">
                    {pendingDossiers.length}
                  </span>
                </div>
                <a
                  href="#/workflows"
                  className="text-xs font-semibold text-[#102A4C] hover:text-[#193D6B] flex items-center gap-1"
                >
                  <span>Tous les circuits</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="space-y-3">
                {pendingDossiers.slice(0, 3).map((d) => (
                  <div
                    key={d.id}
                    className="p-4 rounded-xl border border-stone-200/80 bg-white hover:bg-stone-50 hover:border-stone-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-3xs"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-2 py-0.5 rounded shadow-3xs">
                          {d.id}
                        </span>
                        <span className="text-xs font-bold text-stone-900 truncate">
                          {d.title}
                        </span>
                        {d.isConfidentialCCAS && (
                          <span className="text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200 px-2 py-0.5 rounded-full shrink-0">
                            {d.confidentialBadge || 'Accès restreint · Secret professionnel CCAS'}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-stone-500">
                        <span>{d.circuitLabel}</span>
                        <span>·</span>
                        <span className="truncate">{d.applicant}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border flex items-center gap-1 ${
                          d.slaStatus === 'warning'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-stone-100 text-stone-800 border-stone-200'
                        }`}
                      >
                        <Clock className="w-2.5 h-2.5" />
                        <span>{d.slaDeadline}</span>
                      </span>

                      <a
                        href={`#/workflows?dossier=${d.id}`}
                        className="px-2.5 py-1.5 rounded-md border border-stone-200 bg-white hover:bg-stone-50 text-stone-700 font-semibold text-xs transition-colors flex items-center gap-1 shadow-3xs"
                      >
                        <Eye className="w-3 h-3 text-stone-500" />
                        <span>Voir l'acte</span>
                      </a>

                      <a
                        href={`#/workflows?dossier=${d.id}&action=sign`}
                        className="px-3 py-1.5 rounded-md bg-[#102A4C] hover:bg-[#193D6B] text-white font-semibold text-xs shadow-3xs transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <Check className="w-3 h-3" />
                        <span>Ouvrir & Signer</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Activité récente des services */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                    Activité récente des services
                  </h3>
                </div>
                <span className="text-[11px] text-stone-400 font-medium">Temps réel</span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex items-start gap-3 p-3 rounded-xl bg-stone-50/60 border border-stone-100">
                  <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 font-bold text-xs mt-0.5">
                    CTM
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-stone-800 font-medium">
                      <strong>Jean-Marc Morvan (CTM)</strong> a visé l'avis technique pour <em>Rue des Ajoncs</em>
                    </p>
                    <p className="text-[10px] text-stone-400 mt-0.5">Il y a 25 minutes · Avis favorable sans réserve</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-xl bg-stone-50/60 border border-stone-100">
                  <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center shrink-0 font-bold text-xs mt-0.5">
                    ADS
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-stone-800 font-medium">
                      <strong>Nouveau Cerfa déposé</strong> par le pétitionnaire <em>SARL Armor Aménagement</em>
                    </p>
                    <p className="text-[10px] text-stone-400 mt-0.5">Il y a 1 heure · DP-2026-051 en cours de complétude</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-xl bg-stone-50/60 border border-stone-100">
                  <div className="w-7 h-7 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center shrink-0 font-bold text-xs mt-0.5">
                    @CTES
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-stone-800 font-medium">
                      <strong>Contrôle de légalité télétransmis</strong> à la Préfecture via @CTES
                    </p>
                    <p className="text-[10px] text-stone-400 mt-0.5">Hier 16:45 · Arrêté voirie scellé SHA-256 acquitté</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Lateral Column (35% / 4 cols) — Échéances & Raccourcis */}
          <div className="lg:col-span-4 space-y-5">
            {/* Prochaines échéances & Séances */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center gap-2 border-b border-stone-100 pb-3">
                <Calendar className="w-4 h-4 text-stone-600" />
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Prochaines échéances & Séances
                </h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200/80 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-stone-900">Bureau municipal</span>
                    <span className="text-[10px] font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-1.5 py-0.2 rounded">
                      Séance
                    </span>
                  </div>
                  <p className="text-[11px] text-stone-600">Lundi 23 nov. · 09:30 · Salle du Conseil</p>
                  <p className="text-[10px] text-stone-400">Ordre du jour : arbitrages budgétaires et voirie</p>
                </div>

                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200/80 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-stone-900">Fin délai SLA ADS</span>
                    <span className="text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.2 rounded">
                      Délai légal
                    </span>
                  </div>
                  <p className="text-[11px] text-stone-600">20/11/2026 · 18h · PC-2026-042</p>
                  <p className="text-[10px] text-stone-400">Pétitionnaire M. Kervadec</p>
                </div>

                <div className="p-3 rounded-xl bg-stone-50 border border-stone-200/80 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-stone-900">Conseil municipal</span>
                    <span className="text-[10px] font-bold text-purple-700 bg-purple-50 border border-purple-200 px-1.5 py-0.2 rounded">
                      Délibérations
                    </span>
                  </div>
                  <p className="text-[11px] text-stone-600">Jeudi 26 nov. · 18:30 · M57 & Décisions</p>
                  <p className="text-[10px] text-stone-400">Validation des tarifs périscolaires et voirie</p>
                </div>
              </div>
            </div>

            {/* Raccourcis Directs */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center gap-2 border-b border-stone-100 pb-3">
                <Sparkles className="w-4 h-4 text-[#102A4C]" />
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Raccourcis
                </h3>
              </div>

              <div className="space-y-2">
                {commissionCfg.shortcuts.map((sc, scIdx) => {
                  const isLaunch = sc.actionHash === '/workflows?launch=1';
                  const isDeleg = sc.actionHash === '#open-delegation';
                  const displayLabel = sc.label.startsWith('+ ') ? sc.label.slice(2) : sc.label;
                  if (isLaunch || isDeleg) {
                    return (
                      <button
                        key={scIdx}
                        type="button"
                        onClick={() => isLaunch ? setIsLaunchModalOpen(true) : setIsDelegationOpen(true)}
                        className={`w-full p-2.5 rounded-md font-semibold text-xs flex items-center justify-between transition-colors cursor-pointer shadow-3xs ${
                          sc.primary ? 'bg-[#102A4C] hover:bg-[#193D6B] text-white' : 'bg-stone-50 hover:bg-stone-100 text-stone-800 border border-stone-200'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          {sc.iconName === 'plus' && <Plus className="w-4 h-4" />}
                          {sc.iconName === 'user-check' && <UserCheck className="w-4 h-4 text-amber-600" />}
                          {sc.iconName === 'eye' && <Eye className="w-4 h-4" />}
                          {sc.iconName === 'file-plus' && <FileText className="w-4 h-4" />}
                          {sc.iconName === 'coins' && <Coins className="w-4 h-4 text-amber-600" />}
                          {sc.iconName === 'calendar' && <Calendar className="w-4 h-4" />}
                          {sc.iconName === 'alert-triangle' && <AlertTriangle className="w-4 h-4 text-amber-600" />}
                          {sc.iconName === 'map' && <MapPin className="w-4 h-4" />}
                          <span>{displayLabel}</span>
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                      </button>
                    );
                  }
                  return (
                    <a
                      key={scIdx}
                      href={sc.actionHash.startsWith('/') ? `#${sc.actionHash}` : sc.actionHash}
                      className={`w-full p-2.5 rounded-md font-semibold text-xs flex items-center justify-between transition-colors shadow-3xs ${
                        sc.primary ? 'bg-[#102A4C] hover:bg-[#193D6B] text-white' : 'bg-stone-50 hover:bg-stone-100 text-stone-800 border border-stone-200'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {sc.iconName === 'plus' && <Plus className="w-4 h-4" />}
                        {sc.iconName === 'user-check' && <UserCheck className="w-4 h-4 text-amber-600" />}
                        {sc.iconName === 'eye' && <Eye className="w-4 h-4" />}
                        {sc.iconName === 'file-plus' && <FileText className="w-4 h-4" />}
                        {sc.iconName === 'coins' && <Coins className="w-4 h-4 text-amber-600" />}
                        {sc.iconName === 'calendar' && <Calendar className="w-4 h-4" />}
                        {sc.iconName === 'alert-triangle' && <AlertTriangle className="w-4 h-4 text-amber-600" />}
                        {sc.iconName === 'map' && <MapPin className="w-4 h-4" />}
                        <span>{displayLabel}</span>
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                    </a>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <MayorValidationLaunchModal
        isOpen={isLaunchModalOpen}
        onClose={() => setIsLaunchModalOpen(false)}
        onLaunch={(newDossier) => {
          setDossiers((prev) => [newDossier, ...prev]);
          setIsLaunchModalOpen(false);
          toast.success(`Circuit « ${newDossier.title} » initié avec succès !`);
          window.location.hash = `/workflows?dossier=${newDossier.id}`;
        }}
      />

      <AbsenceDelegationModal
        isOpen={isDelegationOpen}
        onClose={() => setIsDelegationOpen(false)}
      />
    </div>
  );
}
