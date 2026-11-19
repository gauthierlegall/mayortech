import React, { useState, useEffect } from 'react';
import { 
  UserCheck, 
  Calendar, 
  ShieldCheck, 
  AlertCircle, 
  X, 
  CheckCircle2, 
  Clock, 
  ArrowRight,
  UserX
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';

interface AbsenceDelegationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDelegationChange?: (active: boolean, delegateName: string) => void;
}

export function AbsenceDelegationModal({
  isOpen,
  onClose,
  onDelegationChange
}: AbsenceDelegationModalProps) {
  const [isActive, setIsActive] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem('mayortech_absence_delegation');
      return stored ? JSON.parse(stored).active : false;
    } catch {
      return false;
    }
  });

  const [startDate, setStartDate] = useState('2026-11-20');
  const [endDate, setEndDate] = useState('2026-11-27');
  const [delegate, setDelegate] = useState('Valérie LE GUEN · Adjointe à l’Urbanisme & Travaux');
  const [scope, setScope] = useState('all');

  useEffect(() => {
    try {
      const stored = localStorage.getItem('mayortech_absence_delegation');
      if (stored) {
        const parsed = JSON.parse(stored);
        setIsActive(parsed.active);
        if (parsed.delegate) setDelegate(parsed.delegate);
      }
    } catch {}
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    const data = {
      active: isActive,
      startDate,
      endDate,
      delegate,
      scope,
      titulaire: 'Gwenn LE BIHAN · DGS adjointe'
    };
    try {
      localStorage.setItem('mayortech_absence_delegation', JSON.stringify(data));
      window.dispatchEvent(new CustomEvent('mayortech:delegation-changed', { detail: data }));
    } catch {}

    if (onDelegationChange) {
      onDelegationChange(isActive, delegate);
    }

    if (isActive) {
      toast.success(`Délégation de signature activée vers ${delegate.split('·')[0].trim()} jusqu’au ${endDate}.`);
    } else {
      toast.info('Suppléance désactivée. Vous reprenez la signature directe de vos dossiers.');
    }

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-150 text-slate-900">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-amber-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center border border-amber-300">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 leading-snug">
                Déclarer une absence & Suppléant
              </h3>
              <p className="text-xs text-slate-500">
                Délégation temporaire de signature et d'approbation d'actes
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 text-xs">
          {/* Main Toggle */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <div className="font-bold text-slate-900 text-sm">
                Activer la suppléance de visa
              </div>
              <p className="text-slate-500 text-xs mt-0.5">
                Transfère automatiquement les dossiers en attente à votre suppléant(e).
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-600"></div>
            </label>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                Date de début
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-medium focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                Date de fin (inclus)
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-medium focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500"
                />
              </div>
            </div>
          </div>

          {/* Delegate selection */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
              Suppléant(e) désigné(e)
            </label>
            <select
              value={delegate}
              onChange={(e) => setDelegate(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-semibold focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 cursor-pointer"
            >
              <option value="Valérie LE GUEN · Adjointe à l’Urbanisme & Travaux">
                Valérie LE GUEN · Adjointe à l’Urbanisme & Travaux
              </option>
              <option value="Dominique CAP · Maire de Plougastel">
                Dominique CAP · Maire de Plougastel
              </option>
              <option value="Erwan KERVRAN · Directeur des Services Techniques (CTM)">
                Erwan KERVRAN · Directeur des Services Techniques (CTM)
              </option>
            </select>
          </div>

          {/* Scope selection */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
              Périmètre de délégation
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setScope('all')}
                className={`p-2.5 rounded-xl border text-left transition-colors cursor-pointer ${
                  scope === 'all'
                    ? 'border-amber-500 bg-amber-50/50 text-amber-900 font-bold'
                    : 'border-slate-200 bg-white text-slate-700'
                }`}
              >
                <div className="text-xs">Tous les circuits</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Arrêtés, Permis ADS & Marchés</div>
              </button>

              <button
                type="button"
                onClick={() => setScope('emergency_only')}
                className={`p-2.5 rounded-xl border text-left transition-colors cursor-pointer ${
                  scope === 'emergency_only'
                    ? 'border-amber-500 bg-amber-50/50 text-amber-900 font-bold'
                    : 'border-slate-200 bg-white text-slate-700'
                }`}
              >
                <div className="text-xs">Urgences SLA &lt; 24h</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Dossiers critiques uniquement</div>
              </button>
            </div>
          </div>

          {/* Notice */}
          <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200 text-amber-900 text-[11px] flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              Un arrêté municipal portant subdélégation temporaire sera automatiquement annexé aux visas émis par votre suppléant(e) pendant cette période.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="text-xs font-semibold text-slate-700"
          >
            Annuler
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold"
          >
            {isActive ? 'Activer la suppléance' : 'Enregistrer'}
          </Button>
        </div>
      </div>
    </div>
  );
}
