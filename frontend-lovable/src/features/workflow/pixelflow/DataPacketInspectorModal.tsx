import React from 'react';
import { X, ShieldCheck, Box, History, FileText, CheckCircle2, Hash, User, Calendar } from 'lucide-react';

export interface PacketData {
  tokenId: string;
  businessKey: string;
  title: string;
  initiator: string;
  scenario: string;
  variables: Record<string, any>;
  trail: { nodeName: string; timestamp: string; status: string }[];
  sealHash?: string;
}

interface DataPacketInspectorModalProps {
  packet: PacketData | null;
  onClose: () => void;
}

export function DataPacketInspectorModal({ packet, onClose }: DataPacketInspectorModalProps) {
  if (!packet) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in font-sans">
      <div className="relative w-full max-w-2xl bg-slate-950 border border-cyan-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header with glassmorphism accent */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-cyan-500/10 border border-cyan-500/40 rounded-xl text-cyan-400">
              <ShieldCheck size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">
                  Inspecteur Régalien Cerfa & BPMN
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30">
                  EN DIRECT
                </span>
              </div>
              <h3 className="text-sm font-black text-white tracking-tight flex items-center gap-2">
                <span>Dossier : {packet.businessKey}</span>
                <span className="text-xs text-slate-400 font-normal font-mono">(Ville de Plougastel-Daoulas)</span>
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
            aria-label="Fermer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-300">
          {/* Cerfa Documents Row */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Pièces Justificatives Cerfa Scellées
            </span>
            <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
              <span className="px-2 py-1 rounded-lg bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 font-semibold">
                <CheckCircle2 size={11} /> Cerfa 13406*12
              </span>
              <span className="px-2 py-1 rounded-lg bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 font-semibold">
                <CheckCircle2 size={11} /> PCMI-2 Plan de Masse (1/200)
              </span>
              <span className="px-2 py-1 rounded-lg bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 font-semibold">
                <CheckCircle2 size={11} /> PCMI-4 Notice Paysagère
              </span>
              <span className="px-2 py-1 rounded-lg bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 font-semibold">
                <CheckCircle2 size={11} /> PCMI-6 Insertion 3D ABF
              </span>
            </div>
          </div>
          {/* Metadata Card */}
          <div className="grid grid-cols-2 gap-3 p-3 bg-slate-900/40 border border-slate-800/80 rounded-xl">
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Intitulé du Dossier</span>
              <span className="font-semibold text-slate-200 block truncate">{packet.title}</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Initié par</span>
              <div className="flex items-center gap-1.5 font-medium text-slate-200">
                <User size={13} className="text-slate-400" />
                <span>{packet.initiator}</span>
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block">ID Jeton (Token)</span>
              <span className="text-cyan-400 font-mono text-[11px]">{packet.tokenId}</span>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Scénario Actif</span>
              <span className="text-amber-400 font-semibold">{packet.scenario}</span>
            </div>
          </div>

          {/* Variables Payload */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
              <FileText size={14} className="text-cyan-400" />
              <span>Variables d'État & Charge Utile (JSON)</span>
            </div>
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl font-mono text-[11px] overflow-x-auto text-emerald-300">
              <pre>{JSON.stringify(packet.variables, null, 2)}</pre>
            </div>
          </div>

          {/* Milestone Trail */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
              <History size={14} className="text-cyan-400" />
              <span>Trajet des Bâtiments Visités</span>
            </div>
            <div className="space-y-1.5">
              {packet.trail.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-2 bg-slate-900/30 border border-slate-800/60 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-cyan-950 border border-cyan-500/40 text-cyan-400 flex items-center justify-center text-[10px] font-bold">
                      {i + 1}
                    </span>
                    <span className="font-semibold text-slate-200">{t.nodeName}</span>
                  </div>
                  <div className="flex items-center gap-3 text-slate-400 text-[11px]">
                    <span>{t.timestamp}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/15 text-emerald-400 font-semibold">
                      {t.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cryptographic Seal */}
          {packet.sealHash && (
            <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-xl flex items-start gap-3">
              <ShieldCheck size={20} className="text-emerald-400 shrink-0 mt-0.5" />
              <div className="space-y-1 overflow-hidden">
                <span className="text-[11px] font-bold text-emerald-300 block">
                  Empreinte Numérique Certifiée SHA-256
                </span>
                <span className="font-mono text-[10px] text-emerald-400/80 break-all block">
                  {packet.sealHash}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold transition active:scale-95 text-xs shadow"
          >
            Reprendre la Simulation
          </button>
        </div>
      </div>
    </div>
  );
}
