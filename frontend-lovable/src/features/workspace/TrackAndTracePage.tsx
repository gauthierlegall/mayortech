import React, { useState } from 'react';
import { 
  Building2, 
  CheckCircle2, 
  Clock, 
  FileText, 
  UploadCloud, 
  ShieldCheck, 
  FileCheck, 
  ExternalLink,
  Calendar,
  AlertCircle,
  HelpCircle,
  Check
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface TrackAndTracePageProps {
  token?: string;
}

interface Milestone {
  id: number;
  label: string;
  subtitle: string;
  status: 'completed' | 'current' | 'upcoming';
  date?: string;
  details: string;
}

const DEFAULT_MILESTONES: Milestone[] = [
  {
    id: 1,
    label: '1. Dépôt & Enregistrement',
    subtitle: 'Cerfa 13406*12 complet',
    status: 'completed',
    date: '12/10/2026',
    details: 'Dossier jugé recevable par le guichet unique de Plougastel-Daoulas. Récépissé délivré sous le n° PC-2026-042.'
  },
  {
    id: 2,
    label: '2. Instruction & Consultations',
    subtitle: 'Avis techniques en cours',
    status: 'current',
    date: 'En cours (délai : 12/12/2026)',
    details: 'Avis conforme ABF reçu favorable. Consultation voirie favorable. Examen de conformité au Plan Local d’Urbanisme (PLU).'
  },
  {
    id: 3,
    label: '3. Décision & Signature',
    subtitle: 'Arrêté municipal du Maire',
    status: 'upcoming',
    date: 'Prévu début déc. 2026',
    details: 'Rédaction du projet d’arrêté de permis de construire et signature par Dominique Cap, Maire.'
  },
  {
    id: 4,
    label: '4. Délivrance & Affichage',
    subtitle: 'Notification officielle',
    status: 'upcoming',
    date: 'Sous 8 jours après signature',
    details: 'Notification exécutoire au demandeur par voie électronique certifiée et affichage réglementaire en mairie.'
  }
];

export function TrackAndTracePage({ token: propToken }: TrackAndTracePageProps) {
  const [token] = useState(() => {
    if (propToken) return propToken;
    const hash = typeof window !== 'undefined' ? window.location.hash : '';
    const match = hash.match(/suivi\/([^/?]+)/);
    return match ? match[1] : 'PC-2026-042-LE-GALL';
  });

  const [dossier] = useState({
    ref: 'PC-2026-042',
    title: 'Extension d’habitation & Toiture Ardoise naturelle',
    petitioner: 'Mme et M. Hervé LE GALL',
    address: '14 hent Ty-Ar-Braz, 29470 Plougastel-Daoulas',
    cadastre: 'Section AK n° 142 (Surface projet : 48 m²)',
    submissionDate: '12 octobre 2026',
    deadlineDate: '12 décembre 2026',
    instructeur: 'Service Urbanisme & Aménagement (Instructeur : M. Paul Cueff)'
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedReceipt, setUploadedReceipt] = useState<{
    fileName: string;
    date: string;
    sha256: string;
  } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleSimulateDrop = () => {
    // Allows 1-click test file selection
    const mockFile = new File(
      ['Notice architecturale d\'intégration paysagère Ty-Ar-Braz'], 
      'PCMI4_Notice_integration_paysagere.pdf', 
      { type: 'application/pdf' }
    );
    setSelectedFile(mockFile);
  };

  const handleSubmitPiece = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !uploadedReceipt) return;

    setIsUploading(true);
    setTimeout(() => {
      setIsUploading(false);
      setUploadedReceipt({
        fileName: selectedFile?.name || 'PCMI4_Notice_integration_paysagere.pdf',
        date: new Date().toLocaleString('fr-FR', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }),
        sha256: '9f83a21b47c0e812d46e3a958b97a2e5c8e01bf3654f8902d13b60e928507da4'
      });
      setSelectedFile(null);
      toast.success('Document téléversé avec succès', {
        description: 'La pièce complémentaire a été horodatée et transmise au service instructeur.'
      });
    }, 600);
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-6 px-4 sm:px-6 font-sans">
      {/* Republican header stripe */}
      <div className="h-1.5 w-full bg-linear-to-r from-[#102A4C] via-[#FFFFFF] to-[#9F1239] rounded-t-lg mb-0" />

      {/* Main Container */}
      <div className="bg-[#FFFFFF] border border-stone-200/90 rounded-b-lg shadow-xs overflow-hidden">
        {/* Header Institutionnel */}
        <header className="px-6 py-5 border-b border-stone-200 bg-[#FAF9F5]/70 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-[#102A4C] text-white flex items-center justify-center shrink-0">
              <Building2 className="w-5 h-5 text-white" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-stone-900 tracking-tight text-sm">
                  Ville de Plougastel-Daoulas
                </span>
                <span className="text-stone-300">·</span>
                <span className="text-xs text-stone-600 font-medium">Guichet Urbanisme</span>
              </div>
              <h1 className="text-base sm:text-lg font-bold text-[#102A4C] m-0">
                Suivi public d’autorisation d’urbanisme
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-center">
            <span className="text-xs text-stone-500">Accès sécurisé tiers</span>
            <span className="font-mono text-xs bg-stone-100 text-stone-700 px-2.5 py-1 rounded border border-stone-200">
              {token.slice(0, 16)}…
            </span>
          </div>
        </header>

        {/* Dossier Summary Card */}
        <div className="p-6 border-b border-stone-200">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-sm font-bold text-[#102A4C]">{dossier.ref}</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-[#102A4C] border border-blue-200">
                  Permis de Construire
                </span>
              </div>
              <h2 className="text-lg font-semibold text-stone-900 m-0">
                {dossier.title}
              </h2>
              <p className="text-xs text-stone-600 mt-1">
                Demandeur : <strong className="text-stone-800 font-medium">{dossier.petitioner}</strong> · {dossier.address}
              </p>
            </div>
            <div className="sm:text-right shrink-0">
              <span className="text-[11px] uppercase tracking-wider text-stone-500 font-medium block">
                Échéance réglementaire
              </span>
              <span className="text-sm font-semibold text-stone-900">
                {dossier.deadlineDate}
              </span>
              <span className="text-xs text-stone-500 block mt-0.5">
                Déposé le {dossier.submissionDate}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-[#FAF9F5] p-3 rounded border border-stone-200/80">
            <div>
              <span className="text-stone-500">Localisation cadastrale :</span>{' '}
              <span className="text-stone-800 font-medium">{dossier.cadastre}</span>
            </div>
            <div>
              <span className="text-stone-500">Service instructeur :</span>{' '}
              <span className="text-stone-800 font-medium">{dossier.instructeur}</span>
            </div>
          </div>
        </div>

        {/* Stepper : 4 Jalons */}
        <div className="p-6 border-b border-stone-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-500 m-0">
              Avancement de l’instruction (4 étapes)
            </h3>
            <span className="text-xs text-[#0F766E] font-medium flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#0F766E]" />
              Étape 2 en cours
            </span>
          </div>

          <div className="space-y-4">
            {DEFAULT_MILESTONES.map((milestone) => {
              const isCompleted = milestone.status === 'completed';
              const isCurrent = milestone.status === 'current';
              const isUpcoming = milestone.status === 'upcoming';

              return (
                <div 
                  key={milestone.id}
                  className={`flex items-start gap-3.5 p-3.5 rounded-lg border transition-colors ${
                    isCurrent 
                      ? 'bg-amber-50/40 border-amber-300' 
                      : isCompleted 
                        ? 'bg-stone-50/60 border-stone-200' 
                        : 'bg-white border-stone-200/60 opacity-75'
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {isCompleted && (
                      <div className="w-6 h-6 rounded-full bg-[#0F766E] text-white flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                    )}
                    {isCurrent && (
                      <div className="w-6 h-6 rounded-full bg-[#B45309] text-white flex items-center justify-center font-bold text-xs">
                        2
                      </div>
                    )}
                    {isUpcoming && (
                      <div className="w-6 h-6 rounded-full bg-stone-100 text-stone-400 border border-stone-300 flex items-center justify-center font-semibold text-xs">
                        {milestone.id}
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                      <h4 className="text-sm font-semibold text-stone-900 m-0">
                        {milestone.label}
                      </h4>
                      {milestone.date && (
                        <span className={`text-xs font-medium ${isCurrent ? 'text-amber-800' : 'text-stone-500'}`}>
                          {milestone.date}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-stone-600 mt-0.5 m-0">
                      {milestone.subtitle}
                    </p>
                    <p className="text-xs text-stone-700 mt-1.5 leading-relaxed m-0">
                      {milestone.details}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Déposer une pièce manquante (Formulaire 1 clic) */}
        <section className="p-6 bg-[#FAF9F5]/40" aria-labelledby="piece-manquante-title">
          <div className="flex items-center gap-2 mb-3">
            <UploadCloud className="w-5 h-5 text-[#102A4C]" aria-hidden="true" />
            <h3 id="piece-manquante-title" className="text-sm font-bold text-[#102A4C] m-0">
              Déposer une pièce complémentaire
            </h3>
          </div>

          <p className="text-xs text-stone-600 mb-4 leading-relaxed">
            Pour compléter l’instruction technique sans délai, vous pouvez déposer directement le document demandé par le service instructeur (ex. notice d’intégration ou plan de masse actualisé).
          </p>

          {uploadedReceipt ? (
            <div className="bg-[#F0FDFA] border border-[#99F6E4] rounded-lg p-4">
              <div className="flex items-start gap-3">
                <FileCheck className="w-5 h-5 text-[#0F766E] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-[#0F766E] m-0">
                    Dépôt enregistré & horodaté avec succès
                  </h4>
                  <p className="text-xs text-stone-700 mt-1 m-0">
                    Fichier : <strong className="font-mono">{uploadedReceipt.fileName}</strong>
                  </p>
                  <p className="text-xs text-stone-600 mt-0.5 m-0">
                    Date et heure de versement : {uploadedReceipt.date}
                  </p>
                  <div className="mt-2.5 p-2 bg-white rounded border border-stone-200 text-[11px] font-mono text-stone-600 break-all">
                    <span className="font-sans font-semibold text-stone-500 block">Empreinte SHA-256 certifiée :</span>
                    {uploadedReceipt.sha256}
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-[#CCFBF1] flex justify-end">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setUploadedReceipt(null)}
                  className="text-xs text-[#0F766E] border-[#0F766E]/40 hover:bg-[#CCFBF1]"
                >
                  Déposer un autre document
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmitPiece} className="border border-dashed border-stone-300 rounded-lg p-5 bg-white text-center">
              <div className="max-w-md mx-auto space-y-3">
                <div className="flex items-center justify-center">
                  <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center text-stone-500">
                    <FileText className="w-6 h-6 text-[#102A4C]" />
                  </div>
                </div>

                <div>
                  <label htmlFor="file-upload" className="cursor-pointer block text-xs font-semibold text-stone-800">
                    {selectedFile ? selectedFile.name : 'Sélectionnez le document à téléverser (PDF, JPG, PNG)'}
                  </label>
                  <span className="text-[11px] text-stone-500 block mt-0.5">
                    Pièce demandée : <strong className="text-stone-700">PCMI4 - Notice descriptive d’intégration paysagère</strong> (max 10 Mo)
                  </span>
                  <input
                    id="file-upload"
                    type="file"
                    className="sr-only"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={handleFileChange}
                  />
                </div>

                {!selectedFile && (
                  <div className="pt-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleSimulateDrop}
                      className="text-xs text-[#102A4C] border-stone-300 hover:bg-stone-50"
                    >
                      Sélectionner le fichier modèle PCMI4
                    </Button>
                  </div>
                )}

                {selectedFile && (
                  <div className="pt-2 flex items-center justify-center gap-2">
                    <Button
                      type="submit"
                      disabled={isUploading}
                      className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs px-4 py-2 font-medium"
                    >
                      {isUploading ? 'Transmission en cours…' : 'Transmettre la pièce complémentaire'}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedFile(null)}
                      className="text-xs text-stone-500 hover:text-stone-800"
                    >
                      Annuler
                    </Button>
                  </div>
                )}
              </div>
            </form>
          )}
        </section>

        {/* Pied de page institutionnel */}
        <footer className="px-6 py-4 bg-stone-50 border-t border-stone-200 text-xs text-stone-500 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#0F766E] shrink-0" />
            <span>Portail citoyen sécurisé · Conforme Code de l’Urbanisme (art. R*423-1 et s.)</span>
          </div>
          <div className="text-right">
            <span>Mairie de Plougastel-Daoulas · 02 98 37 57 57</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
