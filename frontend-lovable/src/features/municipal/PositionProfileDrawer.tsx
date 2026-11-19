import React from 'react';
import { 
  X, Shield, KeyRound, Mail, Phone, Building2, User, CheckCircle2, 
  ExternalLink, ArrowRight, Award, Lock, Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface OrganigramNode {
  id: string;
  type: 'executive' | 'administration' | 'commission' | 'service' | 'agent';
  title: string;
  holder: string;
  matricule: string;
  niveau: number;
  role: 'reader' | 'editor' | 'admin';
  color: string;
  category: string;
  email: string;
  delegation_signature?: boolean;
  telephone?: string;
  suppleant?: string;
}

interface PositionProfileDrawerProps {
  node: OrganigramNode | null;
  onClose: () => void;
  onSelectNode?: (matricule: string) => void;
}

const NIVEAU_DESCRIPTIONS: Record<number, { title: string; desc: string; color: string }> = {
  0: { title: 'Niveau 0 · Invité / Démo Publique', desc: 'Consultation anonymisée de la démo publique. Aucun accès aux pièces internes régaliennes.', color: 'bg-slate-900 border-slate-700 text-slate-300' },
  1: { title: 'Niveau 1 · Lecteur Sectoriel', desc: 'Conseiller municipal ou membre suppléant. Consultation des dossiers sans vote direct ni signature.', color: 'bg-blue-950 border-blue-800 text-blue-300' },
  2: { title: 'Niveau 2 · Rédacteur / Instructeur ADS', desc: 'Instructeur ADS, comptable, gestionnaire CCAS. Instruction technique des dossiers Cerfa et rédaction des actes.', color: 'bg-emerald-950 border-emerald-800 text-emerald-300' },
  3: { title: 'Niveau 3 · Chef de Service / Pôle', desc: 'Responsable Urbanisme, Travaux, Finances, Enfance. Validation technique, visa intermédiaire et ordonnancement.', color: 'bg-amber-950 border-amber-800 text-amber-300' },
  4: { title: 'Niveau 4 · Ordonnateur / Élu Délégué', desc: 'Maire, Adjoints au Maire délégués, Membres CAO. Visas politiques régaliens, arbitrages budgétaires et signature d’actes.', color: 'bg-purple-950 border-purple-800 text-purple-300' },
  5: { title: 'Niveau 5 · Administrateur Général / DGS', desc: 'Directeur Général des Services. Gestion intégrale du référentiel, clôture, révocation et scellement SHA-256.', color: 'bg-rose-950 border-rose-800 text-rose-300' }
};

export function PositionProfileDrawer({ node, onClose, onSelectNode }: PositionProfileDrawerProps) {
  if (!node) return null;

  const niveauInfo = NIVEAU_DESCRIPTIONS[node.niveau] || NIVEAU_DESCRIPTIONS[1];

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[420px] bg-slate-950/95 border-l border-slate-800 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-200 backdrop-blur-2xl ring-1 ring-white/10 text-slate-100">
      {/* Header */}
      <div 
        className="p-6 text-white flex items-start justify-between relative overflow-hidden border-b border-white/10"
        style={{ 
          background: `linear-gradient(135deg, ${node.color || '#0284c7'}dd 0%, #0f172a 100%)` 
        }}
      >
        <div className="space-y-1.5 z-10">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-lg bg-black/40 text-cyan-300 border border-cyan-800/50">
              {node.category}
            </span>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-black/40 text-white border border-white/20">
              {node.matricule}
            </span>
          </div>
          <h2 className="text-xl font-black leading-tight text-white">{node.title}</h2>
          <p className="text-sm font-semibold text-slate-200">{node.holder}</p>
        </div>
        <button 
          onClick={onClose}
          className="text-white/80 hover:text-white p-1.5 rounded-xl bg-black/20 hover:bg-black/40 transition-colors z-10 border border-white/10"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs font-sans">
        {/* Responsibility Gauge (0 to 5) */}
        <div className="space-y-3 bg-slate-900/80 p-4 rounded-2xl border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 uppercase tracking-wider">
              <Award className="w-4 h-4 text-purple-400" />
              Niveau Régalien Municipal
            </span>
            <span className="text-xs font-mono font-black text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded-lg border border-cyan-800/60">
              {node.niveau} / 5
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden flex border border-slate-800">
            {[1, 2, 3, 4, 5].map(step => (
              <div
                key={step}
                className={`flex-1 border-r border-slate-900 last:border-0 transition-all ${
                  step <= node.niveau ? 'bg-gradient-to-r from-cyan-500 to-blue-500' : 'bg-transparent'
                }`}
              />
            ))}
          </div>

          <div className="pt-2">
            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-lg border inline-block ${niveauInfo.color}`}>
              {niveauInfo.title}
            </span>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              {niveauInfo.desc}
            </p>
          </div>
        </div>

        {/* Identity & Contact */}
        <div className="space-y-2.5">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Coordonnées Sécurisées RH
          </h3>
          <div className="space-y-2">
            <div className="flex items-center gap-2.5 text-xs text-slate-200 bg-slate-900/70 p-3 rounded-xl border border-slate-800">
              <Mail className="w-4 h-4 text-cyan-400 flex-shrink-0" />
              <span className="font-mono truncate">{node.email || 'courriel@ville-plougastel.bzh'}</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-slate-200 bg-slate-900/70 p-3 rounded-xl border border-slate-800">
              <Phone className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>02 98 37 57 57 (Poste Standard Plougastel)</span>
            </div>
          </div>
        </div>

        {/* Powers & Delegations */}
        <div className="space-y-2.5">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Prérogatives & Contrôle d'Accès (ABAC / RBAC)
          </h3>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-slate-900/70 border border-slate-800">
              <span className="text-slate-400">Rôle Noyau Casbin :</span>
              <span className="font-mono font-bold uppercase text-slate-200 bg-slate-800 px-2 py-0.5 rounded-lg border border-slate-700">
                {node.role}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-slate-900/70 border border-slate-800">
              <span className="text-slate-400">Délégation de Signature :</span>
              {node.delegation_signature ? (
                <span className="font-bold text-emerald-400 flex items-center gap-1.5 bg-emerald-950/80 px-2 py-0.5 rounded-lg border border-emerald-800/60">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Arrêté Municipal Actif
                </span>
              ) : (
                <span className="text-slate-500 font-mono">Non habilité</span>
              )}
            </div>

            <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-slate-900/70 border border-slate-800">
              <span className="text-slate-400">Authentification Forte TOTP :</span>
              <span className="font-bold text-cyan-300 flex items-center gap-1.5 bg-cyan-950/80 px-2 py-0.5 rounded-lg border border-cyan-800/60">
                <Shield className="w-3.5 h-3.5 text-cyan-400" />
                Exigée Keycloak 26.8
              </span>
            </div>
          </div>
        </div>

        {/* Designated Substitute */}
        <div className="space-y-2 border-t border-slate-800/80 pt-4">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Suppléance & Continuité de Service
          </h3>
          <div className="p-3.5 bg-purple-950/40 border border-purple-800/60 rounded-2xl space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-purple-200">
                Régime de Suppléance :
              </span>
              <span className="font-mono text-purple-300 text-[10px] bg-purple-900/80 px-2 py-0.5 rounded-lg border border-purple-700/60">
                Arrêté 2026-DEL
              </span>
            </div>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              En cas d'absence temporaire, les visas et paraphes sont délégués automatiquement avec la mention légale <em>« Pour l'ordonnateur en titre et par délégation »</em>.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/90 flex items-center justify-end gap-2">
        <Button 
          variant="outline" 
          size="sm" 
          onClick={onClose} 
          className="w-full bg-slate-900 text-slate-200 font-bold border-slate-700 hover:bg-slate-800 rounded-xl"
        >
          Fermer la Fiche d'Habilitation
        </Button>
      </div>
    </div>
  );
}
