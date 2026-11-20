import React from 'react';
import { X, Command } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  if (!isOpen) return null;

  const shortcuts = [
    { key: 'J', label: 'Dossier suivant dans la file' },
    { key: 'K', label: 'Dossier précédent dans la file' },
    { key: 'V', label: 'Valider / Émarger le dossier actif' },
    { key: 'R', label: 'Renvoyer pour correction (focus sur le motif)' },
    { key: 'P', label: 'Basculer l’affichage des pièces jointes' },
    { key: '?', label: 'Ouvrir cet aide-mémoire des raccourcis' },
    { key: 'Esc', label: 'Fermer les modales et tiroirs actifs' },
  ];

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-xs animate-in fade-in duration-150 font-sans"
      onClick={onClose}
    >
      <div 
        className="bg-[#F7F7F5] border border-stone-200 rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-150 text-stone-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-stone-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            <Command className="w-4 h-4 text-[#102A4C]" />
            <h2 className="text-sm font-bold text-[#102A4C]">Raccourcis clavier parapheur</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
            title="Fermer (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Shortcuts list */}
        <div className="p-5 divide-y divide-stone-200 text-xs">
          {shortcuts.map((sc) => (
            <div key={sc.key} className="py-2.5 flex items-center justify-between first:pt-0 last:pb-0">
              <span className="text-stone-700 font-medium">{sc.label}</span>
              <kbd className="px-2 py-1 rounded border border-stone-300 bg-white font-mono text-[11px] font-bold text-[#102A4C] shadow-3xs">
                {sc.key}
              </kbd>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-2.5 bg-white border-t border-stone-200 text-right">
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold text-stone-600 hover:text-stone-900 px-3 py-1 rounded-md hover:bg-stone-100 transition-colors cursor-pointer"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}
