import React, { useMemo } from 'react';
import { X, QrCode, Printer, ExternalLink, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { generateQrMatrix, matrixToSvgPath } from './qrGenerator';

interface QrCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  actRef: string;
  actTitle: string;
}

export function QrCodeModal({ isOpen, onClose, actRef, actTitle }: QrCodeModalProps) {
  if (!isOpen) return null;

  const publicUrl = useMemo(() => {
    const origin = window.location.origin;
    return `${origin}/#/registre-public/${encodeURIComponent(actRef)}`;
  }, [actRef]);

  const { path, totalSize } = useMemo(() => {
    const matrix = generateQrMatrix(publicUrl);
    return matrixToSvgPath(matrix, 6);
  }, [publicUrl]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-xs animate-in fade-in duration-150 font-sans"
      onClick={onClose}
    >
      <div 
        className="bg-[#F7F7F5] border border-stone-200 rounded-2xl shadow-xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-150 text-stone-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            <QrCode className="w-4 h-4 text-[#102A4C]" />
            <h2 className="text-sm font-bold text-[#102A4C]">Affichage légal & QR Code souverain</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
            title="Fermer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body / Affiche officielle pour panneau d'affichage */}
        <div className="p-6 space-y-4">
          <div className="p-5 bg-white border border-stone-200 rounded-xl shadow-2xs text-center space-y-4">
            
            {/* Header officiel */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">
                République Française · Ville de Plougastel-Daoulas
              </p>
              <h3 className="text-sm font-serif font-bold text-[#102A4C] mt-1">
                AVIS D'AFFICHAGE RÉGLEMENTAIRE
              </h3>
            </div>

            {/* Acte info */}
            <div className="py-2 border-y border-stone-200/80 text-left space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase text-stone-500">Réf. Acte :</span>
                <span className="font-mono text-xs font-bold text-[#102A4C]">{actRef}</span>
              </div>
              <p className="text-xs font-medium text-stone-800 line-clamp-2">
                {actTitle}
              </p>
            </div>

            {/* Vector SVG QR Code */}
            <div className="flex flex-col items-center justify-center p-3 bg-stone-50 rounded-xl border border-stone-200/60 inline-block mx-auto">
              <svg
                width={totalSize}
                height={totalSize}
                viewBox={`0 0 ${totalSize} ${totalSize}`}
                className="max-w-[180px] max-h-[180px] w-full h-auto"
                shapeRendering="crispEdges"
              >
                <rect width={totalSize} height={totalSize} fill="#FFFFFF" />
                <path d={path} fill="#102A4C" />
              </svg>
              <p className="text-[10px] font-mono text-stone-500 mt-2">
                Scannez pour consulter l'acte scellé
              </p>
            </div>

            {/* Public URL */}
            <div className="text-[11px] text-stone-600 bg-stone-50 p-2 rounded-lg border border-stone-200/60 break-all">
              <a 
                href={`/#/registre-public/${encodeURIComponent(actRef)}`} 
                target="_blank" 
                rel="noreferrer"
                className="text-[#102A4C] hover:underline font-mono text-[10px] flex items-center justify-center gap-1"
              >
                <span>{publicUrl}</span>
                <ExternalLink size={12} className="shrink-0" />
              </a>
            </div>

            <div className="flex items-center justify-center gap-1.5 text-[10px] text-stone-500">
              <ShieldCheck className="w-3.5 h-3.5 text-[#0F766E]" />
              <span>Conforme article L. 2131-1 du CGCT (Publication électronique officielle)</span>
            </div>
          </div>
        </div>

        {/* Footer : Exactly 1 Primary Full Button */}
        <div className="px-6 py-3.5 bg-white border-t border-stone-200 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold text-stone-600 hover:text-stone-900 px-3 py-1.5 rounded-lg hover:bg-stone-100 transition-colors cursor-pointer"
          >
            Fermer
          </button>
          <Button
            type="button"
            onClick={handlePrint}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 shadow-2xs cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Imprimer l'avis d'affichage</span>
          </Button>
        </div>

      </div>
    </div>
  );
}
