import React, { useState, useEffect } from 'react';
import {
  Inbox,
  CheckCircle2,
  Clock,
  ArrowRight,
  HardHat,
  Calendar,
  Plus,
  UserCheck,
  FileText,
  Building2,
  MapPin,
  ChevronRight,
  ShieldCheck,
  Check,
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

interface CommissionScheduleEvent {
  title: string;
  badge: string;
  badgeColor: string;
  datetime: string;
  description: string;
}

interface CommissionActivity {
  tag: string;
  tagBg: string;
  tagColor: string;
  htmlText: React.ReactNode;
  timeAgo: string;
}

export function TodayDashboardView() {
  const { session, state, activeCommissionId } = useWorkspace();
  const { organization } = useOrganizationModules();
  const commissionCfg = getCommissionConfig(activeCommissionId);

  const [dossiers, setDossiers] = useState<ValidationDossier[]>(INITIAL_DOSSIERS);
  const [isEluFocusMode, setIsEluFocusMode] = useState<boolean>(() => {
    return localStorage.getItem('mayortech_focus_elu_mode') === 'true';
  });

  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);
  const [isDelegationOpen, setIsDelegationOpen] = useState(false);

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

  // 100% strict scoping for Schedule & Events
  const getCommissionEvents = (): CommissionScheduleEvent[] => {
    if (activeCommissionId === 'commission-1') {
      return [
        {
          title: "Commission d'Appel d'Offres (CAO)",
          badge: 'Marchés',
          badgeColor: 'bg-stone-100 text-[#102A4C] border-stone-200',
          datetime: 'Mardi 24 nov. · 14:00 · Salle des Commissions',
          description: 'Attribution Lot 2 Voirie & Marché MP-2026-008',
        },
        {
          title: 'Conseil municipal (DOB & Décisions)',
          badge: 'Finances',
          badgeColor: 'bg-purple-50 text-purple-800 border-purple-200',
          datetime: 'Jeudi 26 nov. · 18:30 · Salle d’Honneur',
          description: 'Arbitrages budgétaires M57 et décisions modificatives',
        },
        {
          title: 'Clôture exercice budgétaire M57',
          badge: 'Délai légal',
          badgeColor: 'bg-amber-50 text-amber-800 border-amber-200',
          datetime: '30 nov. 2026 · Trésorerie Principale',
          description: 'Transmission des états financiers et mandats',
        },
      ];
    }

    if (activeCommissionId === 'commission-2') {
      return [
        {
          title: 'Commission permanente CCAS',
          badge: 'Aides urgence',
          badgeColor: 'bg-rose-50 text-rose-800 border-rose-200',
          datetime: 'Mercredi 25 nov. · 10:00 · Salle Guérin',
          description: 'Examen des aides facultatives (Art. L.226-13)',
        },
        {
          title: 'Commission Restauration scolaire',
          badge: 'Périscolaire',
          badgeColor: 'bg-stone-100 text-[#102A4C] border-stone-200',
          datetime: 'Vendredi 27 nov. · 14:30 · Pôle Enfance',
          description: 'Arbitrage tarification sociale au quotient familial',
        },
        {
          title: 'Renouvellement convention CAF / CCAS',
          badge: 'Convention',
          badgeColor: 'bg-purple-50 text-purple-800 border-purple-200',
          datetime: '05 déc. 2026 · Direction Générale',
          description: 'Dépôt du bilan d’activité annuel et subvention',
        },
      ];
    }

    if (activeCommissionId === 'commission-3') {
      return [
        {
          title: 'Bureau municipal (Arbitrages voirie)',
          badge: 'Séance',
          badgeColor: 'bg-stone-100 text-[#102A4C] border-stone-200',
          datetime: 'Lundi 23 nov. · 09:30 · Salle du Conseil',
          description: 'Validation planning chantiers CTM et arrêtés',
        },
        {
          title: 'Fin délai SLA ADS',
          badge: 'Délai légal',
          badgeColor: 'bg-amber-50 text-amber-800 border-amber-200',
          datetime: '20/11/2026 · 18:00 · PC-2026-042',
          description: 'Pétitionnaire M. Kervadec · Permis Ty-Ar-Braz',
        },
        {
          title: 'Réception de chantier CTM',
          badge: 'Chantier',
          badgeColor: 'bg-teal-50 text-teal-800 border-teal-200',
          datetime: 'Mercredi 25 nov. · 11:00 · Rue de Brest',
          description: 'Levée des réserves enrobés et réseaux pluviaux',
        },
      ];
    }

    // Default transversal
    return [
      {
        title: 'Bureau municipal',
        badge: 'Séance',
        badgeColor: 'bg-stone-100 text-[#102A4C] border-stone-200',
        datetime: 'Lundi 23 nov. · 09:30 · Salle du Conseil',
        description: 'Ordre du jour : arbitrages transversaux et instances',
      },
      {
        title: 'Fin délai SLA ADS',
        badge: 'Délai légal',
        badgeColor: 'bg-amber-50 text-amber-800 border-amber-200',
        datetime: '20/11/2026 · 18:00 · PC-2026-042',
        description: 'Pétitionnaire M. Kervadec',
      },
      {
        title: 'Conseil municipal',
        badge: 'Délibérations',
        badgeColor: 'bg-purple-50 text-purple-800 border-purple-200',
        datetime: 'Jeudi 26 nov. · 18:30 · M57 & Décisions',
        description: 'Délibérations budgétaires et instances communales',
      },
    ];
  };

  // 100% strict scoping for Recent Activities
  const getCommissionActivities = (): CommissionActivity[] => {
    if (activeCommissionId === 'commission-1') {
      return [
        {
          tag: 'FIN',
          tagBg: 'bg-stone-100',
          tagColor: 'text-[#102A4C]',
          htmlText: (
            <span>
              <strong>Valérie Gestin (Finances)</strong> a émis le bon de commande M57 pour les fournitures administratives
            </span>
          ),
          timeAgo: 'Il y a 25 minutes · Mandat certifié et scellé',
        },
        {
          tag: 'MP',
          tagBg: 'bg-purple-100',
          tagColor: 'text-purple-800',
          htmlText: (
            <span>
              <strong>Rapport d’analyse CAO finalisé</strong> pour le marché public <em>MP-2026-008</em>
            </span>
          ),
          timeAgo: 'Il y a 1 heure · Avis de publication BOAMP transmis',
        },
        {
          tag: '@CTES',
          tagBg: 'bg-stone-100',
          tagColor: 'text-stone-700',
          htmlText: (
            <span>
              <strong>Délibération budgétaire télétransmise</strong> à la Préfecture via @CTES
            </span>
          ),
          timeAgo: 'Hier 16:45 · Délibération scellée SHA-256 acquittée',
        },
      ];
    }

    if (activeCommissionId === 'commission-2') {
      return [
        {
          tag: 'CCAS',
          tagBg: 'bg-rose-100',
          tagColor: 'text-rose-800',
          htmlText: (
            <span>
              <strong>Commission d’attribution</strong> a instruit le dossier confidentiel <em>CCAS-2026-089</em>
            </span>
          ),
          timeAgo: 'Il y a 30 minutes · Secret professionnel Art. L.226-13',
        },
        {
          tag: 'ENF',
          tagBg: 'bg-purple-100',
          tagColor: 'text-purple-800',
          htmlText: (
            <span>
              <strong>Campagne inscriptions scolaires</strong> validée pour 14 familles
            </span>
          ),
          timeAgo: 'Il y a 2 heures · Calculs quotient familial mis à jour',
        },
        {
          tag: '@CTES',
          tagBg: 'bg-stone-100',
          tagColor: 'text-stone-700',
          htmlText: (
            <span>
              <strong>Convention CCAS télétransmise</strong> en Préfecture via @CTES
            </span>
          ),
          timeAgo: 'Hier 15:10 · Transmission scellée e-Bourgogne',
        },
      ];
    }

    if (activeCommissionId === 'commission-3') {
      return [
        {
          tag: 'CTM',
          tagBg: 'bg-emerald-100',
          tagColor: 'text-emerald-800',
          htmlText: (
            <span>
              <strong>Jean-Marc Morvan (CTM)</strong> a visé l’avis technique pour <em>Rue des Ajoncs</em>
            </span>
          ),
          timeAgo: 'Il y a 25 minutes · Avis favorable sans réserve',
        },
        {
          tag: 'ADS',
          tagBg: 'bg-stone-100',
          tagColor: 'text-[#102A4C]',
          htmlText: (
            <span>
              <strong>Nouveau Cerfa déposé</strong> par le pétitionnaire <em>SARL Armor Aménagement</em>
            </span>
          ),
          timeAgo: 'Il y a 1 heure · DP-2026-051 en cours de complétude',
        },
        {
          tag: '@CTES',
          tagBg: 'bg-stone-100',
          tagColor: 'text-stone-700',
          htmlText: (
            <span>
              <strong>Arrêté de voirie télétransmis</strong> à la Préfecture via @CTES
            </span>
          ),
          timeAgo: 'Hier 16:45 · Arrêté voirie scellé SHA-256 acquitté',
        },
      ];
    }

    // Default transversal
    return [
      {
        tag: 'CTM',
        tagBg: 'bg-emerald-100',
        tagColor: 'text-emerald-800',
        htmlText: (
          <span>
            <strong>Jean-Marc Morvan (CTM)</strong> a visé l’avis technique pour <em>Rue des Ajoncs</em>
          </span>
        ),
        timeAgo: 'Il y a 25 minutes · Avis favorable sans réserve',
      },
      {
        tag: 'FIN',
        tagBg: 'bg-stone-100',
        tagColor: 'text-[#102A4C]',
        htmlText: (
          <span>
            <strong>Trésorerie municipale</strong> a visé le mandat M57
          </span>
        ),
        timeAgo: 'Il y a 1 heure · Mandat acquitté',
      },
      {
        tag: '@CTES',
        tagBg: 'bg-stone-100',
        tagColor: 'text-stone-700',
        htmlText: (
          <span>
            <strong>Contrôle de légalité télétransmis</strong> à la Préfecture via @CTES
          </span>
        ),
        timeAgo: 'Hier 16:45 · Scellement SHA-256 acquitté',
      },
    ];
  };

  const scheduleEvents = getCommissionEvents();
  const recentActivities = getCommissionActivities();

  return (
    <div className="w-full max-w-7xl mx-auto space-y-5 font-sans text-stone-900 pb-28 sm:pb-12">
      {/* 1. En-tête léger sans carte englobante (Direct sur fond vélin #F7F7F5) */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
          <div className="flex items-baseline gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold text-stone-900 tracking-tight">
              Bonjour {commissionCfg.greetingName}
            </h1>
            <span className="text-xs text-stone-500 font-medium">· {capitalizedDate}</span>
          </div>
          <div className="text-xs font-semibold text-stone-500 flex items-center gap-1.5">
            <span>{commissionCfg.roleTitle}</span>
            <span>·</span>
            <span>{organization?.name || 'Ville de Plougastel-Daoulas'}</span>
          </div>
        </div>

        {/* 2. Bande métrique fine sur 1 ligne (3 colonnes, divide-x, chiffres tabular-nums en #102A4C) - Masquée en Focus Élu */}
        {!isEluFocusMode && (
          <div className="grid grid-cols-3 bg-white border border-stone-200/90 rounded-xl divide-x divide-stone-200 shadow-3xs overflow-hidden">
            {commissionCfg.kpis.map((kpi) => (
              <a
                key={kpi.id}
                href={kpi.filterId ? `#/workflows` : kpi.id === 'kpi-3' && commissionCfg.hasChantiers ? '#/dossiers' : '#/workflows'}
                className="px-4 py-3 hover:bg-stone-50/80 transition-colors flex items-center justify-between group cursor-pointer"
              >
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider truncate">{kpi.title}</p>
                  <p className="text-xl font-bold text-[#102A4C] tabular-nums tracking-tight mt-0.5">{kpi.count}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-stone-300 group-hover:text-[#102A4C] group-hover:translate-x-0.5 transition-all hidden sm:inline" />
              </a>
            ))}
          </div>
        )}
      </div>

      {/* 3. Focus Mode Minimaliste (Zéro carte KPI, salut compact + signatures directes) */}
      {isEluFocusMode ? (
        <div className="bg-white border border-stone-200/90 rounded-2xl p-5 sm:p-6 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-stone-200">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#102A4C] bg-stone-100 border border-stone-200 px-2 py-0.5 rounded">
                Vue Simplifiée Élu · Zéro distraction
              </span>
              <h2 className="text-lg font-bold text-stone-900 mt-1">
                Vos signatures prioritaires ({pendingDossiers.length})
              </h2>
            </div>
          </div>

          <div className="space-y-4">
            {pendingDossiers.map((d) => (
              <div
                key={d.id}
                className="p-5 rounded-2xl border border-stone-200 bg-[#FFFEFC] hover:border-[#102A4C]/40 hover:shadow-xs transition-all space-y-3"
              >
                <div className="h-[2px] w-full bg-gradient-to-r from-[#102A4C] via-stone-200 to-[#9F1239]" />
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
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

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1">
                  <span className="text-xs text-stone-500 font-medium">
                    Pièces justificatives : {getDocumentSummary(d)}
                  </span>
                  <div className="flex items-center gap-2">
                    <a
                      href={`#/workflows?dossier=${d.id}`}
                      className="px-3.5 py-1.5 rounded-lg border border-stone-200 text-stone-700 hover:bg-stone-50 text-xs font-semibold"
                    >
                      Dossier complet
                    </a>
                    <button
                      onClick={() => handleQuickSign(d.id)}
                      className="px-4 py-1.5 rounded-lg bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs font-bold shadow-3xs flex items-center gap-1.5 cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5 text-white" />
                      <span className="text-white">Viser & Signer</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* 4. Vue Standard : 2 Colonnes Responsive */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Colonne Principale (8 cols) — Priorités à traiter & Activité */}
          <div className="lg:col-span-8 space-y-5">
            {/* Priorités à traiter (1 seul bouton par ligne, texte blanc garanti, badge collé au titre) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                <div className="flex items-center gap-2">
                  <Inbox className="w-4 h-4 text-[#102A4C]" />
                  <h2 className="text-sm font-bold text-stone-900 tracking-tight">
                    Priorités à traiter
                  </h2>
                  <span className="text-[11px] font-bold bg-stone-100 text-[#102A4C] border border-stone-200 px-2 py-0.5 rounded-full font-mono tabular-nums">
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
                {pendingDossiers.slice(0, 4).map((d) => (
                  <div
                    key={d.id}
                    onClick={() => {
                      window.location.hash = `/workflows?dossier=${d.id}`;
                    }}
                    className="p-4 rounded-xl border border-stone-200/90 bg-white hover:bg-stone-50/80 hover:border-stone-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-3xs cursor-pointer group"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-2 py-0.5 rounded shadow-3xs">
                          {d.id}
                        </span>
                        <span className="text-xs font-bold text-stone-900 truncate group-hover:text-[#102A4C] transition-colors">
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

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 shrink-0">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border flex items-center justify-center gap-1 self-start sm:self-center ${
                          d.slaStatus === 'warning'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-stone-100 text-stone-800 border-stone-200'
                        }`}
                      >
                        <Clock className="w-2.5 h-2.5" />
                        <span>{d.slaDeadline}</span>
                      </span>

                      {/* Unique Bouton d'action Traiter avec texte blanc strict */}
                      <a
                        href={`#/workflows?dossier=${d.id}&action=sign`}
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: '#ffffff' }}
                        className="w-full sm:w-auto px-4 py-1.5 rounded-lg bg-[#102A4C] hover:bg-[#193D6B] !text-white font-semibold text-xs shadow-3xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer shrink-0"
                      >
                        <Check className="w-3.5 h-3.5 text-white" />
                        <span className="text-white font-semibold">Traiter</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Activité récente des services (Scoping strict 100% sans fuite) */}
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
                {recentActivities.map((act, actIdx) => (
                  <div key={actIdx} className="flex items-start gap-3 p-3 rounded-xl bg-stone-50/70 border border-stone-100">
                    <div className={`w-7 h-7 rounded-lg ${act.tagBg} ${act.tagColor} flex items-center justify-center shrink-0 font-bold text-xs mt-0.5`}>
                      {act.tag}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-stone-800 font-medium">
                        {act.htmlText}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-0.5">{act.timeAgo}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Colonne Latérale (4 cols) — Uniquement Prochaines échéances (Raccourcis supprimé) */}
          <div className="lg:col-span-4 space-y-5">
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center gap-2 border-b border-stone-100 pb-3">
                <Calendar className="w-4 h-4 text-[#102A4C]" />
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Prochaines échéances & Séances
                </h3>
              </div>

              <div className="space-y-3 text-xs">
                {scheduleEvents.map((evt, evtIdx) => (
                  <div key={evtIdx} className="p-3.5 rounded-xl bg-stone-50/70 border border-stone-200/80 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-stone-900">{evt.title}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${evt.badgeColor}`}>
                        {evt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-stone-600 font-medium">{evt.datetime}</p>
                    <p className="text-[10px] text-stone-400">{evt.description}</p>
                  </div>
                ))}
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
