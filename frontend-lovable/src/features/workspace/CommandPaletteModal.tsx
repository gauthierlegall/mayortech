import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Search,
  FileText,
  CheckCircle2,
  ArrowRight,
  CornerDownLeft,
  X,
  ShieldCheck,
  Calendar,
  User,
  HardHat,
  Plus,
  SlidersHorizontal,
  Layers,
  Zap,
  Building2,
  Stamp,
  UserCheck
} from 'lucide-react';
import { useOrganizationModules } from './organization-modules-context';
import { INITIAL_DOSSIERS } from '../workflow/validation/validationData';

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenValidationLaunch?: () => void;
  onOpenDelegation?: () => void;
}

interface PaletteItem {
  id: string;
  category: 'actions' | 'dossiers' | 'annuaire';
  title: string;
  subtitle: string;
  badge?: string;
  badgeColor?: 'blue' | 'emerald' | 'amber' | 'rose' | 'purple';
  icon: React.ReactNode;
  action: () => void;
}

export function CommandPaletteModal({
  isOpen,
  onClose,
  onOpenValidationLaunch,
  onOpenDelegation,
}: CommandPaletteModalProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const { hasModule } = useOrganizationModules();

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Global keydown for palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Trigger open via custom event
          window.dispatchEvent(new CustomEvent('mayortech:open-palette'));
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Catalog of items
  const allItems = useMemo<PaletteItem[]>(() => {
    const items: PaletteItem[] = [
      // Actions Rapides
      {
        id: 'act-launch-validation',
        category: 'actions',
        title: 'Lancer un circuit de validation',
        subtitle: 'Nouvel arrêté de voirie, permis de construire ou marché public',
        badge: 'Validation',
        badgeColor: 'blue',
        icon: <Plus className="w-4 h-4 text-blue-600" />,
        action: () => {
          onClose();
          if (onOpenValidationLaunch) {
            onOpenValidationLaunch();
          } else {
            window.location.hash = '/workflows?launch=1';
          }
        },
      },
      {
        id: 'act-parapheur-mode',
        category: 'actions',
        title: 'Passer en Mode Parapheur (rafale)',
        subtitle: 'Validation séquentielle rapide au clavier des actes en attente',
        badge: 'Rafale',
        badgeColor: 'purple',
        icon: <Zap className="w-4 h-4 text-purple-600" />,
        action: () => {
          onClose();
          window.location.hash = '/workflows?parapheur=1';
        },
      },
    ];

    if (hasModule('travaux_terrain')) {
      items.push({
        id: 'act-constat-terrain',
        category: 'actions',
        title: 'Créer un constat terrain',
        subtitle: 'Signalement voirie, éclairage ou intervention des équipes CTM',
        badge: 'Terrain',
        badgeColor: 'emerald',
        icon: <HardHat className="w-4 h-4 text-emerald-600" />,
        action: () => {
          onClose();
          window.location.hash = '/terrain';
        },
      });
    }

    items.push({
      id: 'act-absence-delegation',
      category: 'actions',
      title: 'Déclarer une absence / suppléant',
      subtitle: 'Délégation automatique de signature pour un élu ou un chef de pôle',
      badge: 'Délégation',
      badgeColor: 'amber',
      icon: <UserCheck className="w-4 h-4 text-amber-600" />,
      action: () => {
        onClose();
        if (onOpenDelegation) {
          onOpenDelegation();
        } else {
          window.dispatchEvent(new CustomEvent('mayortech:open-delegation'));
        }
      },
    });

    items.push({
      id: 'act-config-modules',
      category: 'actions',
      title: 'Activer / désactiver un module',
      subtitle: 'Périmètre modulaire, connecteurs d’État et options de l’organisation',
      badge: 'Paramètres',
      badgeColor: 'blue',
      icon: <SlidersHorizontal className="w-4 h-4 text-slate-600" />,
      action: () => {
        onClose();
        window.location.hash = '/parametres?section=modules';
      },
    });

    // Dossiers & Actes en cours
    INITIAL_DOSSIERS.forEach((d) => {
      items.push({
        id: `dossier-${d.id}`,
        category: 'dossiers',
        title: `${d.id} · ${d.title}`,
        subtitle: `${d.circuitLabel} · ${d.applicant} · ${d.slaDeadline}`,
        badge: d.status === 'signed' ? 'Signé' : d.slaStatus === 'warning' ? 'Urgent' : 'En cours',
        badgeColor: d.status === 'signed' ? 'emerald' : d.slaStatus === 'warning' ? 'rose' : 'blue',
        icon: <FileText className="w-4 h-4 text-blue-600" />,
        action: () => {
          onClose();
          window.location.hash = `/workflows?dossier=${d.id}`;
        },
      });
    });

    // Annuaire & Chantiers
    items.push(
      {
        id: 'ann-maire',
        category: 'annuaire',
        title: 'M. le Maire · Dominique Cap',
        subtitle: 'Exécutif municipal · Titulaire signature régale',
        badge: 'Élu',
        badgeColor: 'purple',
        icon: <Stamp className="w-4 h-4 text-purple-600" />,
        action: () => {
          onClose();
          window.location.hash = '/parametres?section=members';
        },
      },
      {
        id: 'ann-dgs',
        category: 'annuaire',
        title: 'Mme Laurence Guivarc’h · DGS',
        subtitle: 'Direction Générale des Services · Contrôle de légalité',
        badge: 'Direction',
        badgeColor: 'blue',
        icon: <Building2 className="w-4 h-4 text-blue-600" />,
        action: () => {
          onClose();
          window.location.hash = '/parametres?section=members';
        },
      },
      {
        id: 'ann-ctm',
        category: 'annuaire',
        title: 'M. Jean-Marc Morvan · Responsable CTM',
        subtitle: 'Services Techniques municipaux · Avis voirie & réseaux',
        badge: 'Technique',
        badgeColor: 'emerald',
        icon: <HardHat className="w-4 h-4 text-emerald-600" />,
        action: () => {
          onClose();
          window.location.hash = '/parametres?section=members';
        },
      },
      {
        id: 'ann-alizes',
        category: 'annuaire',
        title: 'Chantier · Parvis de l’école des Alizés',
        subtitle: 'TRV-2026-014 · Réfection accès piétons et portail sécurisé',
        badge: 'Chantier',
        badgeColor: 'emerald',
        icon: <HardHat className="w-4 h-4 text-emerald-600" />,
        action: () => {
          onClose();
          window.location.hash = '/dossiers';
        },
      },
      {
        id: 'ann-ajoncs',
        category: 'annuaire',
        title: 'Chantier · Rue des Ajoncs',
        subtitle: 'TRV-2026-021 · Renouvellement du réseau pluvial et voirie',
        badge: 'Chantier',
        badgeColor: 'emerald',
        icon: <HardHat className="w-4 h-4 text-emerald-600" />,
        action: () => {
          onClose();
          window.location.hash = '/dossiers';
        },
      }
    );

    return items;
  }, [hasModule, onClose, onOpenValidationLaunch, onOpenDelegation]);

  // Filtered items
  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems;
    const q = query.toLowerCase().trim();
    return allItems.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        (item.badge && item.badge.toLowerCase().includes(q))
    );
  }, [allItems, query]);

  // Clamp selection
  useEffect(() => {
    if (selectedIndex >= filteredItems.length) {
      setSelectedIndex(Math.max(0, filteredItems.length - 1));
    }
  }, [filteredItems, selectedIndex]);

  // Key navigation
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const current = filteredItems[selectedIndex];
      if (current) {
        current.action();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150 font-sans"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-100 bg-white">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleInputKeyDown}
            placeholder="Rechercher un dossier, un arrêté, un agent ou une action..."
            className="flex-1 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none bg-transparent"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              title="Effacer"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-400 bg-slate-100 border border-slate-200 rounded shadow-3xs">
            Échap
          </kbd>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-3 text-xs">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-slate-500 space-y-1">
              <p className="font-semibold text-slate-700">Aucun résultat trouvé pour « {query} »</p>
              <p className="text-xs text-slate-400">Essayez une référence (ex: PC-2026), un nom ou une rue.</p>
            </div>
          ) : (
            <>
              {/* Group by category */}
              {(['actions', 'dossiers', 'annuaire'] as const).map((cat) => {
                const groupItems = filteredItems.filter((item) => item.category === cat);
                if (groupItems.length === 0) return null;

                const catLabels = {
                  actions: 'Actions rapides',
                  dossiers: 'Dossiers & Actes en cours',
                  annuaire: 'Annuaire & Chantiers municipaux',
                };

                return (
                  <div key={cat} className="space-y-1">
                    <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      {catLabels[cat]}
                    </div>
                    {groupItems.map((item) => {
                      const itemGlobalIndex = filteredItems.indexOf(item);
                      const isSelected = itemGlobalIndex === selectedIndex;

                      return (
                        <div
                          key={item.id}
                          onClick={() => item.action()}
                          onMouseEnter={() => setSelectedIndex(itemGlobalIndex)}
                          className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-blue-50 text-blue-900 ring-1 ring-blue-300 shadow-2xs'
                              : 'text-slate-800 hover:bg-slate-50'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <div
                              className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
                                isSelected ? 'bg-white border-blue-200' : 'bg-slate-100 border-slate-200/80'
                              }`}
                            >
                              {item.icon}
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="font-semibold text-xs text-slate-900 truncate">
                                {item.title}
                              </p>
                              <p className="text-[11px] text-slate-500 truncate">
                                {item.subtitle}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0 ml-3">
                            {item.badge && (
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                                  item.badgeColor === 'rose'
                                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                                    : item.badgeColor === 'emerald'
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : item.badgeColor === 'amber'
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : item.badgeColor === 'purple'
                                    ? 'bg-purple-50 text-purple-700 border-purple-200'
                                    : 'bg-blue-50 text-blue-700 border-blue-200'
                                }`}
                              >
                                {item.badge}
                              </span>
                            )}
                            {isSelected && (
                              <CornerDownLeft className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded font-mono shadow-3xs">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded font-mono shadow-3xs">↓</kbd>
              <span>Naviguer</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded font-mono shadow-3xs">Entrée</kbd>
              <span>Ouvrir</span>
            </span>
          </div>
          <span className="text-[10px] text-slate-400">Recherche instantanée &lt; 50 ms</span>
        </div>
      </div>
    </div>
  );
}
