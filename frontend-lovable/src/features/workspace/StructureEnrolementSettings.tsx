import React, { useState } from 'react';
import { 
  Building2, 
  Users, 
  Network, 
  UserCheck, 
  KeyRound, 
  FileSpreadsheet, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  ShieldCheck, 
  Download, 
  Plus, 
  ArrowRight, 
  Share2, 
  UploadCloud, 
  AlertTriangle,
  UserPlus,
  Compass
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MunicipalDirectoryView } from '../municipal/MunicipalDirectoryView';
import { MunicipalOrganigramCanvas } from '../municipal/MunicipalOrganigramCanvas';
import { EnrollmentApprovalQueue } from '../municipal/EnrollmentApprovalQueue';
import { MunicipalJoinSasModal } from '../municipal/MunicipalJoinSasModal';
import { toast } from 'sonner';

type StructureSubTab = 'organigramme' | 'postes' | 'enrolement' | 'delegations' | 'wizard';

export function StructureEnrolementSettings() {
  const [activeSubTab, setActiveSubTab] = useState<StructureSubTab>('organigramme');
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);

  // Wizard state for Lot B
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3 | 4>(1);
  const [communeInsee, setCommuneInsee] = useState('29189');
  const [communeName, setCommuneName] = useState('Ville de Plougastel-Daoulas');
  const [strateHabitants, setStrateHabitants] = useState('10 000 à 20 000 hab. (Moyenne commune)');
  const [polePilote, setPolePilote] = useState('commission-3');
  const [importMethod, setImportMethod] = useState<'csv' | 'magic_link' | 'proconnect'>('csv');
  const [copiedLink, setCopiedLink] = useState(false);

  const handleCopyLink = () => {
    navigator.clipboard.writeText('https://mayortech.plougastel.bzh/#/join/pole-urbanisme-2026');
    setCopiedLink(true);
    toast.success('Lien d’auto-enrôlement copié dans le presse-papier !');
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const subTabs = [
    { id: 'organigramme' as const, label: 'Organigramme interactif', icon: Network },
    { id: 'postes' as const, label: 'Référentiel des Postes & Droits', icon: Users },
    { id: 'enrolement' as const, label: 'File d’approbation DGS', icon: UserCheck },
    { id: 'wizard' as const, label: 'Assistant d’Enrôlement (4 étapes)', icon: Compass },
  ];

  return (
    <div className="space-y-6">
      {/* Header section with Civic Craft Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-200/90 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#102A4C]" />
            <h2 className="text-xl font-bold text-stone-900 tracking-tight">
              Structure municipale & Enrôlement des agents
            </h2>
          </div>
          <p className="text-xs text-stone-500 mt-1">
            Double hiérarchie (Élus & Administration), délégations de signature régies par arrêtés, suppléances et organigramme vivant.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setIsJoinModalOpen(true)}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs font-semibold px-3 py-1.5 rounded-md flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Sas d’auto-enrôlement</span>
          </Button>
        </div>
      </div>

      {/* Sub Tabs Pill Navigation */}
      <div className="flex items-center gap-2 border-b border-stone-200/80 pb-2 overflow-x-auto text-xs">
        {subTabs.map((st) => {
          const isActive = activeSubTab === st.id;
          return (
            <button
              key={st.id}
              onClick={() => setActiveSubTab(st.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-md font-bold transition-all shrink-0 ${
                isActive
                  ? 'bg-[#102A4C] text-white shadow-xs'
                  : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
              }`}
            >
              <st.icon className="w-4 h-4" />
              <span>{st.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Organigramme React Flow / SVG Canvas */}
      {activeSubTab === 'organigramme' && (
        <div className="bg-white rounded-lg border border-stone-200/90 p-4 shadow-[0_1px_2px_rgba(16,42,76,0.04)]">
          <div className="flex items-center justify-between mb-3 border-b border-stone-100 pb-2">
            <div>
              <h3 className="text-sm font-bold text-stone-900">Arbre Hiérarchique & Chaîne d'Autorité</h3>
              <p className="text-xs text-stone-500">
                Visualisation de la séparation constitutionnelle : Exécutif Délibératif (Maire & Adjoints) et Administration (DGS, Pôles et Agents).
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-stone-500">
              <span className="inline-block w-2.5 h-2.5 rounded-sm bg-blue-900 mr-1" /> Élus
              <span className="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-700 ml-3 mr-1" /> Administration
            </div>
          </div>
          <div className="h-[680px] rounded-md border border-stone-200/80 overflow-hidden bg-[#F7F7F5] relative">
            <MunicipalOrganigramCanvas />
          </div>
        </div>
      )}

      {/* Tab 2: Référentiel des Postes & Habilitations */}
      {activeSubTab === 'postes' && (
        <div className="bg-white rounded-lg border border-stone-200/90 p-4 shadow-[0_1px_2px_rgba(16,42,76,0.04)]">
          <MunicipalDirectoryView />
        </div>
      )}

      {/* Tab 3: File d'Attente DGS */}
      {activeSubTab === 'enrolement' && (
        <div className="bg-white rounded-lg border border-stone-200/90 p-4 shadow-[0_1px_2px_rgba(16,42,76,0.04)]">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-stone-900">File d'Attente d'Approbation Régalienne (DGS)</h3>
            <p className="text-xs text-stone-500">
              Les demandes d'auto-enrôlement ou d'adhésion par code pôle arrivent ici pour attribution du niveau de responsabilité (0 à 5) et affectation de commission avant ouverture des accès.
            </p>
          </div>
          <EnrollmentApprovalQueue />
        </div>
      )}

      {/* Tab 4: Wizard 4 Étapes d'Enrôlement Mairie */}
      {activeSubTab === 'wizard' && (
        <div className="bg-white rounded-lg border border-stone-200/90 p-6 shadow-[0_1px_2px_rgba(16,42,76,0.04)] max-w-4xl mx-auto space-y-6">
          <div className="border-b border-stone-200/90 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] uppercase tracking-[0.08em] font-semibold text-[#102A4C] bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">
                  Parcours d'Installation Mairie
                </span>
                <h3 className="text-lg font-bold text-stone-900 mt-2">
                  Assistant d’Enrôlement & Structure Territoriale
                </h3>
              </div>
              <div className="font-mono text-xs font-bold text-stone-500">
                Étape {wizardStep} sur 4
              </div>
            </div>

            {/* Stepper Header */}
            <div className="grid grid-cols-4 gap-2 mt-4">
              {[
                { step: 1, title: '1. Commune & Strate' },
                { step: 2, title: '2. Enrôlement & Méthode' },
                { step: 3, title: '3. Approbation & Rôles' },
                { step: 4, title: '4. Topologie & Contrôle' },
              ].map((s) => (
                <div
                  key={s.step}
                  onClick={() => setWizardStep(s.step as any)}
                  className={`p-2 rounded-md border text-xs font-semibold cursor-pointer transition-all ${
                    wizardStep === s.step
                      ? 'border-[#102A4C] bg-[#102A4C] text-white shadow-2xs'
                      : wizardStep > s.step
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                      : 'border-stone-200 text-stone-500 hover:bg-stone-50'
                  }`}
                >
                  {s.title}
                </div>
              ))}
            </div>
          </div>

          {/* Step 1: Commune INSEE & Strate */}
          {wizardStep === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500 block mb-1">
                    Nom officiel de la collectivité
                  </label>
                  <input
                    type="text"
                    value={communeName}
                    onChange={(e) => setCommuneName(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-stone-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#102A4C]"
                  />
                </div>
                <div>
                  <label className="text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500 block mb-1">
                    Code INSEE
                  </label>
                  <input
                    type="text"
                    value={communeInsee}
                    onChange={(e) => setCommuneInsee(e.target.value)}
                    className="w-full text-xs px-3 py-2 font-mono border border-stone-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#102A4C]"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500 block mb-1">
                  Strate démographique
                </label>
                <select
                  value={strateHabitants}
                  onChange={(e) => setStrateHabitants(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-stone-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#102A4C]"
                >
                  <option>Moins de 2 000 hab. (Petite commune rurale)</option>
                  <option>2 000 à 10 000 hab. (Bourg centre / Littorale)</option>
                  <option>10 000 à 20 000 hab. (Moyenne commune)</option>
                  <option>Plus de 20 000 hab. (Agglomération / Ville dense)</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500 block mb-1">
                  Pôle / Commission pilote pour le déploiement initial
                </label>
                <select
                  value={polePilote}
                  onChange={(e) => setPolePilote(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-stone-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#102A4C]"
                >
                  <option value="commission-3">Pôle 3 · Urbanisme, Travaux & Ports (Recommandé)</option>
                  <option value="commission-1">Pôle 1 · Finances & Commande Publique</option>
                  <option value="commission-2">Pôle 2 · Action Sociale & CCAS</option>
                  <option value="commission-4">Pôle 4 · Culture & Vie Associative</option>
                  <option value="commission-0">Direction Générale & Mairie (Supervision globale)</option>
                </select>
              </div>

              <div className="pt-4 flex justify-end">
                <Button
                  onClick={() => setWizardStep(2)}
                  className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs px-4 py-2 rounded-md font-semibold flex items-center gap-1.5"
                >
                  <span>Continuer vers l'enrôlement</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 2: Import PDF/CSV OU Liens d'auto-enrôlement */}
          {wizardStep === 2 && (
            <div className="space-y-4">
              <label className="text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500 block">
                Sélectionnez le mode d'ingestion de la structure
              </label>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div
                  onClick={() => setImportMethod('csv')}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    importMethod === 'csv'
                      ? 'border-[#102A4C] bg-blue-50/40 ring-1 ring-[#102A4C]'
                      : 'border-stone-200 hover:border-stone-300 bg-white'
                  }`}
                >
                  <FileSpreadsheet className="w-5 h-5 text-[#102A4C] mb-2" />
                  <h4 className="text-xs font-bold text-stone-900">Import CSV Annuaire</h4>
                  <p className="text-[11px] text-stone-500 mt-1">
                    Chargement d'un fichier CSV formaté avec matricules, statuts et délégations.
                  </p>
                </div>

                <div
                  onClick={() => setImportMethod('magic_link')}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    importMethod === 'magic_link'
                      ? 'border-[#102A4C] bg-blue-50/40 ring-1 ring-[#102A4C]'
                      : 'border-stone-200 hover:border-stone-300 bg-white'
                  }`}
                >
                  <Share2 className="w-5 h-5 text-emerald-700 mb-2" />
                  <h4 className="text-xs font-bold text-stone-900">Liens par Pôle</h4>
                  <p className="text-[11px] text-stone-500 mt-1">
                    Génération d'URLs d'auto-enrôlement <code>/join/:poleToken</code> pour chaque chef de service.
                  </p>
                </div>

                <div
                  onClick={() => setImportMethod('proconnect')}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    importMethod === 'proconnect'
                      ? 'border-[#102A4C] bg-blue-50/40 ring-1 ring-[#102A4C]'
                      : 'border-stone-200 hover:border-stone-300 bg-white'
                  }`}
                >
                  <ShieldCheck className="w-5 h-5 text-purple-700 mb-2" />
                  <h4 className="text-xs font-bold text-stone-900">ProConnect / OIDC</h4>
                  <p className="text-[11px] text-stone-500 mt-1">
                    Fédération d'identité de l'État DINUM avec mappage automatique des attributs SIRET.
                  </p>
                </div>
              </div>

              {/* Detail view depending on method */}
              {importMethod === 'csv' && (
                <div className="border border-dashed border-stone-300 rounded-lg p-6 bg-stone-50/50 text-center space-y-2">
                  <UploadCloud className="w-8 h-8 text-stone-400 mx-auto" />
                  <p className="text-xs font-semibold text-stone-800">
                    Déposez votre fichier <code>annuaire_plougastel_2026.csv</code>
                  </p>
                  <p className="text-[10px] text-stone-500">
                    Colonnes reconnues : matricule, nom, prenom, email, statut, direction, poste, commission_id, niveau, role.
                  </p>
                  <Button size="sm" variant="outline" className="text-xs mt-2">
                    Télécharger le modèle CSV officiel
                  </Button>
                </div>
              )}

              {importMethod === 'magic_link' && (
                <div className="bg-emerald-50/60 border border-emerald-200 rounded-lg p-4 space-y-2">
                  <p className="text-xs font-semibold text-emerald-900">
                    Lien d'enrôlement direct pour le Pôle Urbanisme & Travaux :
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value="https://mayortech.plougastel.bzh/#/join/pole-urbanisme-2026"
                      className="flex-1 text-xs px-3 py-1.5 font-mono bg-white border border-emerald-200 rounded-md text-stone-700"
                    />
                    <Button
                      size="sm"
                      onClick={handleCopyLink}
                      className="bg-emerald-700 hover:bg-emerald-800 text-white text-xs"
                    >
                      {copiedLink ? 'Copié !' : 'Copier'}
                    </Button>
                  </div>
                  <p className="text-[10px] text-emerald-700">
                    Chaque agent qui utilise ce lien arrive dans le Sas et est automatiquement pré-assigné à la Commission 3.
                  </p>
                </div>
              )}

              {importMethod === 'proconnect' && (
                <div className="bg-purple-50/60 border border-purple-200 rounded-lg p-4 text-xs text-purple-900 space-y-1">
                  <p className="font-semibold">Connecteur ProConnect (DINUM) configuré en Bac à sable</p>
                  <p className="text-[11px] text-purple-700">
                    Les agents s'authentifient avec leur adresse institutionnelle. Les attributs d'autorité sont récupérés et insérés comme profil en attente de visa DGS.
                  </p>
                </div>
              )}

              <div className="pt-4 flex justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setWizardStep(1)}
                  className="text-xs"
                >
                  Précédent
                </Button>
                <Button
                  onClick={() => setWizardStep(3)}
                  className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs px-4 py-2 rounded-md font-semibold flex items-center gap-1.5"
                >
                  <span>Passer aux approbations</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Approbation & Rôles */}
          {wizardStep === 3 && (
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <strong>Sécurité & Cloisonnement Régalien :</strong>
                  <p className="text-[11px] mt-0.5">
                    Aucun compte n'a accès aux dossiers avant l'approbation formelle de la DGS ou du Maire. L'approbation attribue une commission stricte et un niveau d'habilitation (0 à 5).
                  </p>
                </div>
              </div>

              <div className="border border-stone-200 rounded-lg p-3 space-y-2">
                <h4 className="text-xs font-bold text-stone-900">Exemple de demande prête à être validée :</h4>
                <div className="bg-[#F7F7F5] p-3 rounded-md border border-stone-200 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-stone-900">Ronan LE GALL</span>
                    <span className="text-stone-500 ml-2">· ronan.legall@ville-plougastel.bzh</span>
                    <div className="text-[11px] text-stone-500 mt-0.5">
                      Poste demandé : <strong>Instructeur ADS & Voirie</strong> · Commission 3
                    </div>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                    Niveau 2 (Instructeur)
                  </span>
                </div>
              </div>

              <div className="pt-4 flex justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setWizardStep(2)}
                  className="text-xs"
                >
                  Précédent
                </Button>
                <Button
                  onClick={() => setWizardStep(4)}
                  className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs px-4 py-2 rounded-md font-semibold flex items-center gap-1.5"
                >
                  <span>Vérifier la topologie & santé</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 4: Topologie & Check-list de Santé */}
          {wizardStep === 4 && (
            <div className="space-y-4">
              <div className="border border-stone-200 rounded-lg p-4 space-y-3">
                <h4 className="text-xs font-bold text-stone-900 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Check-list de santé organisationnelle de la mairie
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-emerald-50 text-emerald-900">
                    <span>1. Ordonnateur en chef (Maire) déclaré avec délégation de signature</span>
                    <span className="font-bold font-mono text-emerald-700">CONFORME</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-emerald-50 text-emerald-900">
                    <span>2. Direction Générale des Services (DGS) opérationnelle</span>
                    <span className="font-bold font-mono text-emerald-700">CONFORME</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-emerald-50 text-emerald-900">
                    <span>3. Cloisonnement CCAS garanti (secret médical & social)</span>
                    <span className="font-bold font-mono text-emerald-700">ÉTANCHE</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-emerald-50 text-emerald-900">
                    <span>4. Suppléances et intérim configurés pour absences</span>
                    <span className="font-bold font-mono text-emerald-700">ACTIF</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 flex justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setWizardStep(3)}
                  className="text-xs"
                >
                  Précédent
                </Button>
                <Button
                  onClick={() => {
                    toast.success('Structure municipale déployée avec succès pour Plougastel-Daoulas !');
                    setActiveSubTab('organigramme');
                  }}
                  className="bg-emerald-700 hover:bg-emerald-800 text-white text-xs px-4 py-2 rounded-md font-semibold flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Finaliser et ouvrir l'organigramme</span>
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sas Modal */}
      <MunicipalJoinSasModal
        isOpen={isJoinModalOpen}
        onClose={() => setIsJoinModalOpen(false)}
        onSuccess={() => {
          setIsJoinModalOpen(false);
          setActiveSubTab('enrolement');
          toast.success('Demande enregistrée dans la file d’attente DGS !');
        }}
      />
    </div>
  );
}
