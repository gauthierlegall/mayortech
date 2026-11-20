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
  ChevronDown,
  ChevronUp,
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

  const [expandedDossierIds, setExpandedDossierIds] = useState<string[]>([
    'DELIB-2026-088',
    'ARR-2026-088',
    'CCAS-2026-089',
  ]);

  const toggleExpandDossier = (id: string) => {
    setExpandedDossierIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);
  const [isDelegationOpen, setIsDelegationOpen] = useState(false);

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
          timeAgo: 'Hier 15:10 · Transmission scellée Mégalis Bretagne',
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
        <div className="px-4 sm:px-0 space-y-0.5">
          <h1 className="text-2xl sm:text-3xl font-bold text-stone-900 tracking-tight">
            Bonjour {commissionCfg.greetingName}
          </h1>
          <p className="text-xs text-stone-500 font-medium">{capitalizedDate}</p>
        </div>

        {/* 2. Bande métrique fine sur 1 ligne (3 colonnes, divide-x, chiffres tabular-nums en #102A4C) */}
        <div className="grid grid-cols-3 bg-white border border-stone-200/90 rounded-xl divide-x divide-stone-200 shadow-3xs overflow-hidden">
          {commissionCfg.kpis.map((kpi) => (
            <a
              key={kpi.id}
              href={kpi.filterId ? `#/workflows` : kpi.id === 'kpi-3' && commissionCfg.hasChantiers ? '#/dossiers' : '#/workflows'}
              className="px-2.5 sm:px-4 py-2 sm:py-3 hover:bg-stone-50/80 transition-colors flex items-center justify-between group cursor-pointer"
            >
              <div className="min-w-0">
                <p className="text-[10px] sm:text-[11px] font-semibold text-stone-500 uppercase tracking-wider truncate"><span className="sm:hidden">{kpi.shortTitle || kpi.title}</span><span className="hidden sm:inline">{kpi.title}</span></p>
                <p className="text-lg sm:text-xl font-bold text-[#102A4C] tabular-nums tracking-tight mt-0.5">{kpi.count}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-stone-300 group-hover:text-[#102A4C] group-hover:translate-x-0.5 transition-all hidden sm:inline" />
            </a>
          ))}
        </div>
      </div>

      {/* 3. Vue Métier : 2 Colonnes Responsive */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Colonne Principale (8 cols) — Priorités à traiter & Activité */}
          <div className="lg:col-span-8 space-y-5">
            {/* Priorités à traiter (Design épuré Civic Distill: Surface unique, divide-y, zéro bouton plein, lignes cliquables) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-stone-900 tracking-tight">
                    Priorités à traiter
                  </h2>
                  <span className="text-[11px] font-semibold text-stone-500 font-mono tabular-nums">
                    ({pendingDossiers.length})
                  </span>
                </div>
                <a
                  href="#/workflows"
                  className="text-xs font-semibold text-[#102A4C] hover:text-[#193D6B] flex items-center gap-1 transition-colors"
                >
                  <span>Tous les circuits</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="divide-y divide-stone-200/70">
                {pendingDossiers.slice(0, 4).map((d) => (
                  <div
                    key={d.id}
                    onClick={() => {
                      window.location.hash = `/workflows?dossier=${d.id}`;
                    }}
                    className="px-5 py-3.5 hover:bg-stone-50/90 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer group"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      {/* Ligne 1: Référence en texte brut sans cadre + Titre complet + Badge critique éventuel */}
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-mono text-xs text-stone-500 shrink-0">
                          {d.id}
                        </span>
                        <span className="text-xs font-bold text-stone-900 group-hover:text-[#102A4C] transition-colors">
                          {d.title}
                        </span>
                        {d.isConfidentialCCAS && (
                          <span className="text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200 px-2 py-0.5 rounded-full shrink-0">
                            {d.confidentialBadge || 'Secret professionnel CCAS'}
                          </span>
                        )}
                      </div>
                      {/* Ligne 2: Métadonnées discrètes */}
                      <div className="flex items-center gap-2 text-[11px] text-stone-500 font-medium">
                        <span>{d.circuitLabel}</span>
                        <span className="text-stone-300">·</span>
                        <span>{d.applicant}</span>
                      </div>
                    </div>

                    {/* Échéance en texte sobre (sans pilule) + Flèche discrète alignée à droite */}
                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      <span
                        className={`text-xs ${
                          d.slaStatus === 'warning'
                            ? 'text-amber-700 font-semibold'
                            : 'text-stone-500 font-medium'
                        }`}
                      >
                        {d.slaDeadline}
                      </span>
                      <ArrowRight className="w-4 h-4 text-stone-300 group-hover:text-[#102A4C] group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Activité récente (Surface épurée sans cartes imbriquées) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
              <div className="px-5 py-4 border-b border-stone-100">
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Activité récente
                </h3>
              </div>

              <div className="divide-y divide-stone-100 text-xs">
                {recentActivities.map((act, actIdx) => (
                  <div key={actIdx} className="flex items-start gap-3 px-5 py-3 hover:bg-stone-50/60 transition-colors">
                    <div className={`w-6 h-6 rounded-md ${act.tagBg} ${act.tagColor} flex items-center justify-center shrink-0 font-bold text-[10px] mt-0.5`}>
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
            <div className="bg-white border border-stone-200/90 rounded-2xl shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
              <div className="px-5 py-4 border-b border-stone-100">
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Échéances & Séances
                </h3>
              </div>

              <div className="divide-y divide-stone-100 text-xs">
                {scheduleEvents.map((evt, evtIdx) => (
                  <div key={evtIdx} className="px-5 py-3 hover:bg-stone-50/60 transition-colors space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-stone-900">{evt.title}</span>
                      <span className={`text-[10px] font-medium text-stone-500`}>
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
