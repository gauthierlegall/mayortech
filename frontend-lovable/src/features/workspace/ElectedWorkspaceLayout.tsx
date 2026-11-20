import React, { useState } from 'react';
import {
  Landmark,
  CheckCircle2,
  CalendarDays,
  HardHat,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Check,
  RotateCcw,
  FileText,
  UserCheck,
  LogOut,
  AlertCircle,
  Building,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ValidationDossier, INITIAL_DOSSIERS } from '../workflow/validation/validationData';
import { CommissionConfig } from './commissionConfig';
import { AbsenceDelegationModal } from './AbsenceDelegationModal';

interface ElectedWorkspaceLayoutProps {
  commissionCfg: CommissionConfig;
  activeCommissionId: string;
  onChangeProfile: (id: string) => Promise<void>;
  onOpenDelegation: () => void;
  delegation: { active: boolean; delegate: string };
  session: any;
  commissions: any[];
  projects: any[];
}

export function ElectedWorkspaceLayout({
  commissionCfg,
  activeCommissionId,
  onChangeProfile,
  onOpenDelegation,
  delegation,
  session,
  commissions,
  projects,
}: ElectedWorkspaceLayoutProps) {
  // Navigation tabs: 'sign' | 'seances' | 'dossiers'
  const [activeTab, setActiveTab] = useState<'sign' | 'seances' | 'dossiers'>('sign');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isDelegationModalOpen, setIsDelegationModalOpen] = useState(false);

  // Validation dossiers state
  const [dossiers, setDossiers] = useState<ValidationDossier[]>(INITIAL_DOSSIERS);
  const [expandedActIds, setExpandedActIds] = useState<string[]>(['MP-2026-008', 'PC-2026-042']);
  const [openPiecesDossierId, setOpenPiecesDossierId] = useState<string | null>(null);
  const [returningDossierId, setReturningDossierId] = useState<string | null>(null);
  const [returnReason, setReturnReason] = useState<string>('');
  const [signNotice, setSignNotice] = useState<string | null>(null);

  // Strict filtering for Mayor:
  // Dossiers that are pending, allowed by commissionCfg, not confidential CCAS,
  // and whose active step is the Mayor (currentStepIndex points to Maire)
  const pendingActsToSign = dossiers.filter((d) => {
    if (d.status !== 'pending') return false;
    if (d.isConfidentialCCAS) return false;
    if (!commissionCfg.allowedDossierIds.includes(d.id)) return false;
    const currentStep = d.steps[d.currentStepIndex];
    if (!currentStep) return false;
    const isMayorStep =
      currentStep.id === 'step-maire' ||
      currentStep.role.toLowerCase().includes('maire') ||
      currentStep.actor.toLowerCase().includes('maire') ||
      d.currentStepIndex === d.steps.length - 1;
    return isMayorStep;
  });

  const toggleExpandAct = (id: string) => {
    setExpandedActIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSignAct = (id: string) => {
    const target = dossiers.find((d) => d.id === id);
    if (!target) return;

    setDossiers((prev) =>
      prev.map((d) => {
        if (d.id !== id) return d;
        const now = new Date();
        const dateStr = now.toLocaleDateString('fr-FR') + ' à ' + now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        const isDelegated = Boolean(delegation.active);
        const authorName = isDelegated ? `${delegation.delegate.split('·')[0].trim()} (Suppléant)` : 'Dominique CAP (Maire)';
        const authorRole = isDelegated ? '1er Adjoint (Par délégation pour le Maire empêché)' : 'Maire de Plougastel-Daoulas';
        const auditComment = isDelegated 
          ? 'Signé pour le Maire empêché par délégation selon arrêté ARR-2026-DEL-001. Empreinte SHA-256 scellée et enregistrée au registre des actes.'
          : 'Acte signé électroniquement. Empreinte SHA-256 scellée et enregistrée au registre des actes.';

        const updatedSteps = d.steps.map((st, idx) => {
          if (idx === d.currentStepIndex) {
            return {
              ...st,
              status: 'completed' as const,
              signedAt: dateStr,
              comment: isDelegated ? 'Signé par suppléance légale (Maire empêché).' : 'Arrêté signé électroniquement et télétransmis en Préfecture (@CTES).',
              sha256: 'a1b2c3d4e5f6' + Math.random().toString(16).substring(2, 6),
            };
          }
          return st;
        });
        return {
          ...d,
          status: 'signed' as const,
          steps: updatedSteps,
          auditTrail: [
            ...d.auditTrail,
            {
              timestamp: dateStr,
              author: authorName,
              role: authorRole,
              action: 'scellement' as const,
              stepName: isDelegated ? 'Signature Suppléant (Délégation) & @CTES' : 'Signature Maire & Télétransmission @CTES',
              comment: auditComment,
              sha256: 'a1b2c3d4e5f67890',
            },
          ],
        };
      })
    );

    const isDelegatedNotice = Boolean(delegation.active);
    setSignNotice(
      isDelegatedNotice
        ? `L’acte ${id} a été signé par suppléance légale pour le Maire empêché (Arrêté n° ARR-2026-DEL-001).`
        : `L’acte ${id} a été signé par Dominique CAP (Maire) et télétransmis au contrôle de légalité (@CTES).`
    );
    setTimeout(() => {
      setSignNotice(null);
    }, 4500);
  };

  const handleReturnToDgs = (id: string) => {
    if (!returnReason.trim()) return;
    setDossiers((prev) =>
      prev.map((d) => {
        if (d.id !== id) return d;
        return {
          ...d,
          status: 'returned' as const,
          currentStepIndex: Math.max(0, d.currentStepIndex - 1),
          auditTrail: [
            ...d.auditTrail,
            {
              timestamp: new Date().toLocaleDateString('fr-FR') + ' à ' + new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
              author: 'Dominique CAP (Maire)',
              role: 'Maire de Plougastel-Daoulas',
              action: 'renvoi' as const,
              stepName: 'Renvoi à la Direction Générale (DGS)',
              comment: `Renvoi par le Maire : ${returnReason.trim()}`,
            },
          ],
        };
      })
    );
    setReturningDossierId(null);
    setReturnReason('');
    setSignNotice(`L’acte ${id} a été renvoyé à la Direction Générale avec vos observations.`);
    setTimeout(() => setSignNotice(null), 4500);
  };

  return (
    <div className="min-h-screen bg-[#F7F7F5] text-stone-900 font-sans flex flex-col antialiased overflow-x-hidden">
      {/* 1. Barre supérieure épurée sur 1 ligne (Logo + Commune | 3 Onglets | Menu Profil) */}
      <header className="h-14 bg-white border-b border-stone-200/90 px-2.5 sm:px-6 flex items-center justify-between shadow-[0_1px_2px_rgba(16,42,76,0.04)] sticky top-0 z-40">
        {/* Gauche : Logo MayorTech. + Ville de Plougastel-Daoulas */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <div className="flex items-center gap-1.5 sm:gap-2">
            <span className="w-7 h-7 rounded-md bg-[#102A4C] text-white flex items-center justify-center shrink-0">
              <Landmark size={16} />
            </span>
            <span className="font-bold text-stone-900 tracking-tight text-sm sm:text-lg">
              MayorTech<span className="text-[#102A4C]">.</span>
            </span>
          </div>
          <span className="hidden lg:inline text-stone-300 font-light">|</span>
          <span className="hidden lg:inline text-xs font-semibold text-stone-600 truncate max-w-[200px]">
            Ville de Plougastel-Daoulas
          </span>
        </div>

        {/* Centre : 3 Onglets sobres */}
        <nav className="flex items-center gap-1 sm:gap-2 text-xs" aria-label="Espace Élu">
          <button
            type="button"
            onClick={() => setActiveTab('sign')}
            className={`px-2 sm:px-3 py-1.5 rounded-md font-bold flex items-center gap-1 sm:gap-1.5 transition-colors cursor-pointer ${
              activeTab === 'sign'
                ? 'bg-[#102A4C] text-white shadow-xs'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
            title="Actes à signer"
          >
            <CheckCircle2 size={14} />
            <span className="hidden sm:inline">À signer</span>
            <span
              className={`text-[10px] sm:text-[11px] font-mono tabular-nums px-1.5 py-0.2 rounded-full ${
                activeTab === 'sign' ? 'bg-white/20 text-white' : 'bg-stone-200 text-stone-800'
              }`}
            >
              {pendingActsToSign.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('seances')}
            className={`px-2 sm:px-3 py-1.5 rounded-md font-bold flex items-center gap-1 sm:gap-1.5 transition-colors cursor-pointer ${
              activeTab === 'seances'
                ? 'bg-[#102A4C] text-white shadow-xs'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
            title="Séances institutionnelles"
          >
            <CalendarDays size={14} />
            <span className="hidden md:inline">Séances & Agenda</span>
            <span className="hidden sm:inline md:hidden">Séances</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('dossiers')}
            className={`px-2 sm:px-3 py-1.5 rounded-md font-bold flex items-center gap-1 sm:gap-1.5 transition-colors cursor-pointer ${
              activeTab === 'dossiers'
                ? 'bg-[#102A4C] text-white shadow-xs'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
            title="Dossiers suivis"
          >
            <HardHat size={14} />
            <span className="hidden md:inline">Dossiers suivis</span>
            <span className="hidden sm:inline md:hidden">Dossiers</span>
          </button>
        </nav>

        {/* Droite : Menu profil discret Dominique Cap · Maire ▾ */}
        <div className="relative shrink-0">
          <button
            type="button"
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-1 sm:gap-2 px-1.5 sm:px-2.5 py-1.5 rounded-lg hover:bg-stone-100 text-stone-800 text-xs font-semibold transition-colors cursor-pointer select-none"
            aria-expanded={isUserMenuOpen}
            aria-label="Menu du Maire"
          >
            <span className="w-6 h-6 rounded-md bg-[#102A4C]/10 text-[#102A4C] font-bold text-[11px] flex items-center justify-center shrink-0">
              DC
            </span>
            <span className="hidden md:inline truncate max-w-[140px]">Dominique Cap · Maire</span>
            <ChevronDown
              size={13}
              className={`text-stone-400 transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {isUserMenuOpen && (
            <div className="absolute right-0 mt-1.5 w-64 bg-white border border-stone-200 rounded-xl shadow-xl p-2 z-50 text-xs space-y-1 animate-in fade-in duration-100">
              <div className="px-2 py-1.5 border-b border-stone-100 mb-1">
                <p className="font-bold text-stone-900">Dominique Cap</p>
                <p className="text-[10px] text-stone-500">Maire de Plougastel-Daoulas</p>
                <p className="text-[10px] text-[#102A4C] font-medium">Cabinet du Maire & Exécutif</p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setIsUserMenuOpen(false);
                  setIsDelegationModalOpen(true);
                }}
                className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-stone-100 text-stone-700 font-medium transition-colors cursor-pointer text-left"
              >
                <UserCheck size={15} className="text-amber-600" />
                <span>Absence & Suppléant</span>
                {delegation.active && (
                  <span className="ml-auto text-[9px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.2 rounded">
                    Actif
                  </span>
                )}
              </button>

              {/* Mode Démonstration : Bascule vers les autres profils pour la présentation */}
              <div className="border-t border-stone-100 pt-1.5 mt-1">
                <p className="text-[10px] font-semibold text-stone-400 uppercase tracking-wider px-2 mb-1">
                  Changer de profil (Démo)
                </p>
                <div className="space-y-0.5">
                  <button
                    type="button"
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      void onChangeProfile('all');
                    }}
                    className="w-full text-left px-2 py-1 rounded hover:bg-stone-100 text-stone-700 text-xs truncate"
                  >
                    0. Direction Générale (Laurence Bernard)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      void onChangeProfile('commission-1');
                    }}
                    className="w-full text-left px-2 py-1 rounded hover:bg-stone-100 text-stone-700 text-xs truncate"
                  >
                    1. Finances & Moyens (Valérie Gestin)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      void onChangeProfile('commission-2');
                    }}
                    className="w-full text-left px-2 py-1 rounded hover:bg-stone-100 text-stone-700 text-xs truncate"
                  >
                    2. Action Sociale & CCAS (Nolwenn Péron)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      void onChangeProfile('commission-3');
                    }}
                    className="w-full text-left px-2 py-1 rounded hover:bg-stone-100 text-stone-700 text-xs truncate"
                  >
                    3. Urbanisme & Travaux (Loïc Kerbrat)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      void onChangeProfile('commission-4');
                    }}
                    className="w-full text-left px-2 py-1 rounded hover:bg-stone-100 text-stone-700 text-xs truncate"
                  >
                    4. Culture & Sport (Jean-Luc Le Gall)
                  </button>
                </div>
              </div>

              <div className="border-t border-stone-100 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    window.location.assign('/connexion.html');
                  }}
                  className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-rose-50 text-rose-700 font-medium transition-colors cursor-pointer text-left"
                >
                  <LogOut size={14} />
                  <span>Se déconnecter</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Notification discrète d'action */}
      {signNotice && (
        <div className="bg-[#0F766E] text-white px-4 py-2.5 text-xs font-semibold flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2 max-w-5xl mx-auto w-full">
            <Check size={16} />
            <span>{signNotice}</span>
          </div>
        </div>
      )}

      {/* Contenu principal selon l'onglet actif */}
      <main className="flex-1 p-3 sm:p-6 max-w-5xl w-full mx-auto">
        {/* ==================================================================== */}
        {/* ONGLET 1 : À SIGNER (N) — LECTURE PAPIER PURE, CIVIC DISTILL STRICT */}
        {/* ==================================================================== */}
        {activeTab === 'sign' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-stone-200">
              <div>
                <h1 className="text-base sm:text-lg font-bold text-stone-900 tracking-tight">
                  Actes en attente de votre signature
                </h1>
                <p className="text-xs text-stone-500">
                  Dossiers instruits par les services et visés par la Direction Générale.
                </p>
              </div>
              <span className="font-mono text-xs font-semibold text-stone-500">
                {pendingActsToSign.length} acte{pendingActsToSign.length > 1 ? 's' : ''} à viser
              </span>
            </div>

            {pendingActsToSign.length === 0 ? (
              <div className="bg-white border border-stone-200 rounded-lg p-8 text-center space-y-2">
                <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center mx-auto">
                  <Check size={20} />
                </div>
                <h3 className="text-sm font-bold text-stone-900">
                  Tous les actes soumis à votre signature ont été traités
                </h3>
                <p className="text-xs text-stone-500 max-w-md mx-auto">
                  Aucun arrêté ou marché public n'est actuellement en attente de votre paraphe. Les nouveaux dossiers visés par la DGS apparaîtront ici automatiquement.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingActsToSign.map((d) => {
                  const isExpanded = expandedActIds.includes(d.id);
                  const isPiecesOpen = openPiecesDossierId === d.id;
                  const isReturning = returningDossierId === d.id;

                  return (
                    <article
                      key={d.id}
                      className="bg-[#FFFEFC] border border-stone-200 rounded-lg shadow-sm overflow-hidden transition-all"
                    >
                      {/* Filet supérieur continu de 2px en Encre Marine #102A4C */}
                      <div className="h-[2px] w-full bg-[#102A4C]" />

                      <div className="p-4 sm:p-5 space-y-3">
                        {/* En-tête : Référence légale (font-mono sans boîte) + SLA à droite */}
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs text-stone-500 tracking-tight">
                            {d.id}
                          </span>
                          <span
                            className={`text-xs font-semibold px-2 py-0.5 rounded ${
                              d.slaStatus === 'warning'
                                ? 'bg-amber-50 text-amber-800'
                                : 'text-stone-500'
                            }`}
                          >
                            Échéance : {d.slaDeadline}
                          </span>
                        </div>

                        {/* Titre de l'acte en typographie éditoriale claire */}
                        <h2 className="text-base sm:text-lg font-semibold text-stone-900 tracking-tight font-serif">
                          {d.title}
                        </h2>

                        {/* Résumé juridique & métadonnées sur une ligne discrète */}
                        <div className="flex items-center gap-2 text-xs text-stone-500 flex-wrap">
                          <span className="font-medium text-stone-700">{d.circuitLabel}</span>
                          <span className="text-stone-300">·</span>
                          <span>Demandeur : {d.applicant}</span>
                          <span className="text-stone-300">·</span>
                          <span>Dépôt : {d.createdAt}</span>
                        </div>

                        {/* Dépliage fluide : Bouton lien sobre avec 1 seule icône Lucide à gauche (zéro double flèche ▴/▾) */}
                        <div className="pt-0.5">
                          <button
                            type="button"
                            onClick={() => toggleExpandAct(d.id)}
                            className="text-xs font-semibold text-[#102A4C] hover:text-[#193D6B] inline-flex items-center gap-1.5 transition-colors cursor-pointer select-none"
                          >
                            {isExpanded ? (
                              <>
                                <ChevronUp size={15} />
                                <span>Masquer l'acte complet</span>
                              </>
                            ) : (
                              <>
                                <ChevronDown size={15} />
                                <span>Lire l'acte complet</span>
                              </>
                            )}
                          </button>
                        </div>

                        {/* Corps de l'acte déplié en Source Serif 4 / Georgia (zéro cartes intérieures autour des Vu... et ARTICLE...) */}
                        {isExpanded ? (
                          <div className="pt-3 border-t border-stone-200/80 space-y-3 font-serif animate-in fade-in duration-150">
                            {/* En-tête administratif sobre */}
                            <div className="text-center pb-2 border-b border-stone-100">
                              <p className="text-[10px] font-bold tracking-widest uppercase text-stone-500 font-sans">
                                RÉPUBLIQUE FRANÇAISE
                              </p>
                              <p className="text-xs font-bold text-stone-900 font-sans">
                                VILLE DE PLOUGASTEL-DAOULAS
                              </p>
                              <p className="text-[10px] text-stone-500 font-sans">
                                Cabinet du Maire & Exécutif
                              </p>
                            </div>

                            {/* Visas continus sans encadrements */}
                            <div className="text-stone-600 text-xs italic leading-relaxed py-1 space-y-0.5">
                              <p>Vu le Code Général des Collectivités Territoriales ;</p>
                              <p>Vu la demande déposée par {d.applicant} sous la référence {d.id} ;</p>
                              <p>Vu les avis techniques préalables et le visa de légalité de la Direction Générale ;</p>
                            </div>

                            {/* Dispositif / Articles de l'acte */}
                            <div className="py-2 text-xs sm:text-sm text-stone-900 leading-relaxed whitespace-pre-line">
                              {d.previewArticle}
                            </div>

                            {/* Bloc de signature officiel avec mention de suppléance si actif */}
                            <div className="pt-3 border-t border-stone-200/80 text-right font-sans text-xs">
                              <p className="text-stone-500 text-[10px]">Fait à Plougastel-Daoulas, le 20/11/2026</p>
                              {delegation.active ? (
                                <div className="space-y-0.5 mt-1">
                                  <p className="font-semibold text-stone-800">Pour le Maire empêché et par délégation,</p>
                                  <p className="font-bold text-[#102A4C] text-xs">{delegation.delegate.split('·')[0].trim()}</p>
                                  <p className="text-[10px] text-stone-500 italic">
                                    Par délégation selon arrêté municipal de suppléance n° ARR-2026-DEL-001 · Scellé eIDAS
                                  </p>
                                </div>
                              ) : (
                                <div className="space-y-0.5 mt-1">
                                  <p className="font-semibold text-stone-800">Pour le Maire de Plougastel-Daoulas,</p>
                                  <p className="font-bold text-[#102A4C] text-xs">Dominique CAP</p>
                                  <p className="text-[10px] text-stone-500 italic">
                                    Maire de Plougastel-Daoulas · Certifié exécutoire sous sa responsabilité
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          /* Aperçu court sans boîte intérieure */
                          <p className="text-xs text-stone-700 italic font-serif line-clamp-2 pt-1 border-t border-stone-100">
                            « {d.previewArticle.split('\n\n')[0]} »
                          </p>
                        )}

                        {/* Tiroir / Affichage inline des pièces justificatives */}
                        {isPiecesOpen && (
                          <div className="bg-stone-50/80 border border-stone-200 rounded-md p-3 text-xs space-y-1.5 animate-in fade-in duration-150">
                            <p className="font-bold text-stone-800 text-[11px] uppercase tracking-wider mb-1">
                              Pièces justificatives certifiées ({d.documents.length})
                            </p>
                            <ul className="divide-y divide-stone-200/60">
                              {d.documents.map((doc, docIdx) => (
                                <li key={docIdx} className="py-1.5 flex items-center justify-between gap-2">
                                  <div className="flex items-center gap-2 min-w-0">
                                    <FileText size={14} className="text-stone-500 shrink-0" />
                                    <span className="font-medium text-stone-800 truncate">{doc.name}</span>
                                    <span className="text-stone-400 text-[10px]">({doc.size})</span>
                                  </div>
                                  <span className="text-[10px] font-mono text-stone-500 shrink-0">
                                    {doc.badge || doc.type}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Divulgation progressive : Renvoi à la DGS avec champ motif */}
                        {isReturning && (
                          <div className="bg-amber-50/60 border border-amber-200 rounded-md p-3 text-xs space-y-2 animate-in fade-in duration-150">
                            <p className="font-bold text-amber-900 text-xs">
                              Motif du renvoi à la Direction Générale (DGS)
                            </p>
                            <textarea
                              value={returnReason}
                              onChange={(e) => setReturnReason(e.target.value)}
                              placeholder="Précisez les rectifications ou compléments attendus des services..."
                              className="w-full p-2 bg-white border border-amber-300 rounded text-xs text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-[#102A4C] h-18 resize-none"
                            />
                            <div className="flex items-center justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  setReturningDossierId(null);
                                  setReturnReason('');
                                }}
                                className="px-2.5 py-1 text-stone-600 hover:text-stone-800 text-xs cursor-pointer"
                              >
                                Annuler
                              </button>
                              <button
                                type="button"
                                onClick={() => handleReturnToDgs(d.id)}
                                disabled={!returnReason.trim()}
                                className="px-3 py-1 bg-amber-800 hover:bg-amber-900 text-white rounded text-xs font-semibold cursor-pointer disabled:opacity-50"
                              >
                                Confirmer le renvoi à la DGS
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Pied de document : SHA-256 + 1 SEUL BOUTON PLEIN PAR ÉCRAN */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-stone-200">
                          {/* Mention sobre et factuelle d'intégrité */}
                          <div className="flex items-center gap-1.5 text-xs text-stone-500">
                            <ShieldCheck size={14} className="text-[#0F766E]" />
                            <span>Intégrité SHA-256 vérifiée · En attente de votre signature</span>
                          </div>

                          {/* Actions : Pièces (lien) · Renvoyer (texte) · 1 SEUL bouton plein 'Signer l'acte' */}
                          <div className="flex items-center gap-3 self-end sm:self-auto flex-wrap">
                            <button
                              type="button"
                              onClick={() =>
                                setOpenPiecesDossierId(isPiecesOpen ? null : d.id)
                              }
                              className="text-xs font-medium text-stone-600 hover:text-[#102A4C] transition-colors cursor-pointer"
                            >
                              {isPiecesOpen
                                ? 'Fermer les pièces'
                                : `Pièces justificatives (${d.documents.length})`}
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                setReturningDossierId(isReturning ? null : d.id);
                                setReturnReason('');
                              }}
                              className="text-xs font-medium text-stone-600 hover:text-amber-800 transition-colors cursor-pointer"
                            >
                              Renvoyer à la DGS
                            </button>

                            {/* 1 SEUL BOUTON PLEIN (Vert Sceau #0F766E) */}
                            <button
                              type="button"
                              onClick={() => handleSignAct(d.id)}
                              className="px-4 py-2 rounded-lg bg-[#0F766E] hover:bg-[#0D655E] text-white text-xs font-bold shadow-sm flex items-center gap-1.5 cursor-pointer transition-colors"
                            >
                              <Check size={14} className="text-white" />
                              <span className="text-white">Signer l'acte</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ==================================================================== */}
        {/* ONGLET 2 : SÉANCES & AGENDA — LISTE ÉPURÉE DIVIDE-Y SUR FOND VÉLIN */}
        {/* ==================================================================== */}
        {activeTab === 'seances' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-stone-200">
              <div>
                <h1 className="text-base sm:text-lg font-bold text-stone-900 tracking-tight">
                  Séances institutionnelles & Agenda du Maire
                </h1>
                <p className="text-xs text-stone-500">
                  Conseils municipaux, réunions de bureau et commissions permanentes.
                </p>
              </div>
            </div>

            <div className="bg-white border border-stone-200 rounded-lg shadow-sm overflow-hidden">
              <div className="divide-y divide-stone-200">
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#102A4C]/10 text-[#102A4C]">
                        Conseil Municipal
                      </span>
                      <span className="font-mono text-xs text-stone-500">Ordinaire · Séance n° 5</span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Conseil Municipal du 26 novembre 2026
                    </h3>
                    <p className="text-xs text-stone-600">
                      18 délibérations inscrites · Salle du Conseil · Quorum prévisionnel : 28/33 élus
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Jeudi 26 nov. · 18h30</p>
                    <p className="text-[11px] text-stone-500">Ordre du jour arrêté</p>
                  </div>
                </div>

                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-50 text-purple-900">
                        Bureau Municipal
                      </span>
                      <span className="font-mono text-xs text-stone-500">Exécutif & Adjoints</span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Réunion des Adjoints · Arbitrages BP 2026
                    </h3>
                    <p className="text-xs text-stone-600">
                      Hôtel de Ville · Examen des attributions CAO Alizés et orientations M57
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Mardi 24 nov. · 09h00</p>
                    <p className="text-[11px] text-stone-500">Cabinet du Maire</p>
                  </div>
                </div>

                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 text-teal-900">
                        Commission Mixte
                      </span>
                      <span className="font-mono text-xs text-stone-500">Pôle Technique</span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Commission Urbanisme & Grands Travaux
                    </h3>
                    <p className="text-xs text-stone-600">
                      Centre Technique Municipal · Bilan des arrêtés de voirie Port du Tinduff
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Jeudi 03 déc. · 10h00</p>
                    <p className="text-[11px] text-stone-500">Salle CTM</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* ONGLET 3 : DOSSIERS SUIVIS — SYNTHÈSE PROJETS COMMUNAUX EN COURS    */}
        {/* ==================================================================== */}
        {activeTab === 'dossiers' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-stone-200">
              <div>
                <h1 className="text-base sm:text-lg font-bold text-stone-900 tracking-tight">
                  Grands dossiers communaux suivis
                </h1>
                <p className="text-xs text-stone-500">
                  Vue d'ensemble sur les opérations d'investissement et chantiers du mandat.
                </p>
              </div>
            </div>

            <div className="bg-white border border-stone-200 rounded-lg shadow-sm overflow-hidden">
              <div className="divide-y divide-stone-200">
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-stone-500">TRV-2026-014</span>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-800">
                        En cours (65 %)
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      École des Alizés · Réhabilitation énergétique globale (Lot 2 CVC)
                    </h3>
                    <p className="text-xs text-stone-600">
                      Budget voté : 1 200 000 € · Attribution CAO en cours de signature · Livraison été 2027
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Pôle Écoles</p>
                    <p className="text-[11px] text-stone-500">Financement M57</p>
                  </div>
                </div>

                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-stone-500">TRV-2026-021</span>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-800">
                        En cours (40 %)
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Port du Tinduff · Réfection de la cale et dragage d'amarrage
                    </h3>
                    <p className="text-xs text-stone-600">
                      Budget voté : 480 000 € · Arrêté de voirie ARR-2026-019 en cours · Desserte maritime
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Pôle Littoral</p>
                    <p className="text-[11px] text-stone-500">Subvention Région</p>
                  </div>
                </div>

                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-stone-500">TRV-2026-008</span>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-800">
                        En cours (85 %)
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Salle du Rivage · Mise aux normes PMR & acoustique
                    </h3>
                    <p className="text-xs text-stone-600">
                      Budget voté : 220 000 € · Réception de chantier prévue mi-décembre 2026
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Pôle Patrimoine</p>
                    <p className="text-[11px] text-stone-500">Fonds verts</p>
                  </div>
                </div>

                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-stone-50/60 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-stone-500">PC-2026-042</span>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-800">
                        En signature
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-stone-900">
                      Extension & Toiture Ty-Ar-Braz (M. & Mme Kervadec)
                    </h3>
                    <p className="text-xs text-stone-600">
                      Instruction ADS terminée · Conforme PLU · Avis ABF favorable
                    </p>
                  </div>
                  <div className="text-right sm:self-center shrink-0">
                    <p className="text-xs font-bold text-stone-900">Pôle Urbanisme</p>
                    <p className="text-[11px] text-stone-500">Dossier ADS</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modal d'absence & suppléance */}
      <AbsenceDelegationModal
        isOpen={isDelegationModalOpen}
        onClose={() => setIsDelegationModalOpen(false)}
      />
    </div>
  );
}
