import React, { useState } from 'react';
import { AlertTriangle, Calendar, ArrowRight, CheckCircle2, SlidersHorizontal, MapPin } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';

export interface TrafficConflict {
  id: string;
  axis: string;
  startDate: string;
  endDate: string;
  overlapDays: number;
  itemA: { ref: string; title: string; type: string; impact: string };
  itemB: { ref: string; title: string; type: string; impact: string };
  resolved: boolean;
}

const DEFAULT_CONFLICT: TrafficConflict = {
  id: 'CONFLICT-VOIRIE-01',
  axis: 'Rue des Ajoncs ↔ Quai du Tinduff',
  startDate: '24/11/2026',
  endDate: '28/11/2026',
  overlapDays: 5,
  itemA: {
    ref: 'ARR-2026-019',
    title: 'Réglementation temporaire Quai du Tinduff',
    type: 'Arrêté de voirie (Alternat feux)',
    impact: 'Circulation sur 1 seule voie régulée par alternat',
  },
  itemB: {
    ref: 'TRV-2026-038',
    title: 'Aménagement et réfection Rue des Ajoncs',
    type: 'Chantier voirie (Enrobé)',
    impact: 'Emprise de voirie et engins de chantier',
  },
  resolved: false,
};

export function RoadTrafficConflictBanner() {
  const [conflict, setConflict] = useState<TrafficConflict>(DEFAULT_CONFLICT);
  const [isArbitrating, setIsArbitrating] = useState(false);
  const [resolutionNotice, setResolutionNotice] = useState<string | null>(null);

  const handleResolve = () => {
    setConflict(prev => ({ ...prev, resolved: true }));
    setIsArbitrating(false);
    setResolutionNotice(
      "Conflit arbitré avec succès : le chantier Rue des Ajoncs est reporté au 02/12/2026. L'arrêté ARR-2026-019 s'exécutera sans perturbation."
    );
  };

  const handleReset = () => {
    setConflict(prev => ({ ...prev, resolved: false }));
    setResolutionNotice(null);
  };

  if (conflict.resolved) {
    return (
      <div className="bg-[#F0FDFA] border border-[#99F6E4] text-[#0F766E] rounded-lg p-3.5 mb-4 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-[#0F766E] shrink-0" />
          <span className="text-xs font-medium">
            {resolutionNotice || 'Conflit de voirie arbitré : aucun chevauchement de circulation actif.'}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleReset}
          className="h-6 text-[11px] text-[#0F766E] hover:bg-[#CCFBF1] underline"
        >
          Réexaminer
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className="bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] rounded-lg p-3.5 mb-4 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-5 h-5 text-[#B45309] shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <div className="flex items-center flex-wrap gap-2 mb-0.5">
                <span className="font-semibold text-xs text-[#B45309] uppercase tracking-wide">
                  Conflit de circulation détecté
                </span>
                <span className="inline-flex items-center gap-1 font-mono text-[11px] bg-amber-100/90 text-amber-900 px-2 py-0.5 rounded border border-amber-300/60 font-medium">
                  <MapPin className="w-3 h-3 text-[#B45309]" />
                  {conflict.axis}
                </span>
                <span className="text-xs text-amber-800 font-medium">
                  (du {conflict.startDate} au {conflict.endDate})
                </span>
              </div>
              <p className="text-xs text-amber-900 m-0 leading-relaxed">
                Deux arrêtés ou chantiers simultanés restreignent le même axe d'accès au port : l'arrêté{' '}
                <strong className="font-semibold">{conflict.itemA.ref}</strong> (alternat feux) chevauche le chantier{' '}
                <strong className="font-semibold">{conflict.itemB.ref}</strong>. Risque de blocage complet du transit.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsArbitrating(true)}
              className="border-amber-300 bg-white text-amber-900 hover:bg-amber-50 text-xs h-8 px-3 font-medium shadow-xs"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 mr-1.5 text-[#B45309]" />
              Arbitrer le calendrier
            </Button>
          </div>
        </div>
      </div>

      {/* Modale d'arbitrage de voirie */}
      <Dialog open={isArbitrating} onOpenChange={setIsArbitrating}>
        <DialogContent className="max-w-lg bg-white p-5 rounded-lg border border-stone-200">
          <DialogTitle className="text-base font-semibold text-[#102A4C] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#B45309]" />
            Arbitrage de circulation · {conflict.axis}
          </DialogTitle>
          <DialogDescription className="text-xs text-stone-600 mb-4">
            Pour éviter l’engorgement simultané de la zone portuaire, choisissez la mesure d’ajustement de calendrier.
          </DialogDescription>

          <div className="space-y-3 mb-5">
            <div className="p-3 rounded border border-stone-200 bg-[#FBFBF9]">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-xs font-semibold text-[#102A4C]">{conflict.itemA.ref}</span>
                <span className="text-xs text-stone-500 font-medium">24/11 → 28/11/2026</span>
              </div>
              <p className="text-xs text-stone-800 font-medium m-0">{conflict.itemA.title}</p>
              <p className="text-[11px] text-stone-500 m-0">{conflict.itemA.impact}</p>
            </div>

            <div className="p-3 rounded border border-stone-200 bg-[#FBFBF9]">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-xs font-semibold text-[#102A4C]">{conflict.itemB.ref}</span>
                <span className="text-xs text-amber-700 font-medium">25/11 → 30/11/2026 (Chevauchement)</span>
              </div>
              <p className="text-xs text-stone-800 font-medium m-0">{conflict.itemB.title}</p>
              <p className="text-[11px] text-stone-500 m-0">{conflict.itemB.impact}</p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsArbitrating(false)}
              className="text-stone-600 border-stone-200 hover:bg-stone-50 text-xs h-8"
            >
              Annuler
            </Button>
            <Button
              size="sm"
              onClick={handleResolve}
              className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs h-8 px-3 font-medium shadow-xs"
            >
              Décaler le chantier au 02/12/2026 (Résoudre)
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
