import React from 'react';
import { 
  X, 
  FileText, 
  ShieldCheck, 
  Building2, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  ExternalLink,
  Hash,
  Send,
  ArrowRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface BpmnDrawerDetails {
  id: string;
  title: string;
  actor: string;
  sla: string;
  description: string;
  piecesCerfa: string[];
  articlesPlu: string[];
  sha256?: string;
  status: 'valid' | 'pending' | 'rejected' | 'warning';
}

interface BpmnDrawerProps {
  details: BpmnDrawerDetails | null;
  onClose: () => void;
  onOpenDecision?: () => void;
}

export const BpmnDrawer: React.FC<BpmnDrawerProps> = ({ details, onClose, onOpenDecision }) => {
  if (!details) return null;

  return (
    <div className="fixed top-[72px] bottom-0 right-0 w-84 md:w-96 bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-200 text-slate-900 font-sans">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-start justify-between bg-slate-50/70">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
              Étape BPMN 2.0
            </span>
            <span className="text-[10px] font-mono font-bold text-slate-500">
              {details.sla}
            </span>
          </div>
          <h2 className="text-sm md:text-base font-bold text-slate-900 leading-snug">
            {details.title}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5 font-medium">
            {details.actor}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          title="Fermer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">

        {/* Description */}
        <div className="space-y-1.5">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <FileText className="w-3.5 h-3.5 text-blue-600" />
            Description Métier & Légale
          </h3>
          <p className="text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 text-[11px]">
            {details.description}
          </p>
        </div>

        {/* Cerfa 13406*12 Documents */}
        <div className="space-y-2">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Pièces Cerfa 13406*12 Requises
          </h3>
          <div className="space-y-1.5">
            {details.piecesCerfa.map((piece, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 border border-slate-200/70 text-slate-700 font-mono text-[11px]"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="font-semibold text-slate-900">{piece}</span>
              </div>
            ))}
          </div>
        </div>

        {/* PLU Articles & Urbanisme */}
        <div className="space-y-2">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
            <Building2 className="w-3.5 h-3.5 text-amber-600" />
            Conformité PLU Plougastel & Législation
          </h3>
          <div className="space-y-1.5">
            {details.articlesPlu.map((art, idx) => (
              <div
                key={idx}
                className="p-2 rounded-lg bg-amber-50/50 border border-amber-200/80 text-amber-900 text-[11px]"
              >
                {art}
              </div>
            ))}
          </div>
        </div>

        {/* Cryptographic SHA-256 Seal (Full hash displayed) */}
        {details.sha256 && (
          <div className="space-y-1.5">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
              Scellement SHA-256 & Parapheur @CTES
            </h3>
            <div className="p-2.5 rounded-lg bg-indigo-50/60 border border-indigo-200/80 space-y-1.5">
              <span className="text-[10px] text-indigo-900 font-bold block">
                Empreinte immuable registre des actes municipaux :
              </span>
              <p className="font-mono text-[10px] text-indigo-950 break-all select-all bg-white p-2 rounded border border-indigo-200 shadow-2xs font-bold">
                {details.sha256}
              </p>
              <div className="flex items-center justify-between text-[10px] text-indigo-700 font-medium pt-0.5">
                <span>Télétransmission @CTES : Transmis</span>
                <span>Norme : eIDAS / RGS**</span>
              </div>

              {/* Interactive Webhook Simulation Button */}
              <div className="pt-2 border-t border-indigo-200/60">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    try {
                      await fetch('/api/v1/connectors/parapheur_pastell/simulate-webhook', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ action: 'signature_complete', dossier_id: details.id })
                      });
                    } catch {}
                    const bordereau = `AR-ACTES-2026-${Math.random().toString(16).substring(2, 8).toUpperCase()}`;
                    window.dispatchEvent(new CustomEvent('mayortech:connector-signed', {
                      detail: { id: details.id, bordereau }
                    }));
                    alert(`Accusé de réception Préfecture reçu !\nBordereau : ${bordereau}\nStatut : Validé et scellé au registre.`);
                  }}
                  className="w-full text-[11px] font-bold text-indigo-700 bg-white hover:bg-indigo-50 border-indigo-300 py-1.5 h-auto flex items-center justify-center gap-1.5 shadow-2xs cursor-pointer"
                >
                  <Send className="w-3 h-3 text-indigo-600" />
                  <span>Simuler signature i-Parapheur + retour @CTES</span>
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/70 flex items-center gap-2">
        <Button
          size="sm"
          onClick={() => {
            onClose();
            if (onOpenDecision) onOpenDecision();
          }}
          className="flex-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <span>Traiter / Valider dans « À valider »</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onClose}
          className="text-xs font-semibold text-slate-700 border-slate-300 hover:bg-slate-100 px-3 cursor-pointer"
        >
          Fermer
        </Button>
      </div>
    </div>
  );
};
