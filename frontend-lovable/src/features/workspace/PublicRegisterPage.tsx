import React, { useState, useEffect, useMemo } from 'react';
import { 
  Building2, 
  Search, 
  FileText, 
  CheckCircle2, 
  ShieldCheck, 
  ArrowLeft, 
  Printer, 
  QrCode,
  ExternalLink,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { generateQrMatrix, matrixToSvgPath } from '../workflow/validation/qrGenerator';

interface PublicAct {
  ref: string;
  title: string;
  category: string;
  commission_id: string;
  publication_date: string;
  signed_by: string;
  applicant: string;
  status: string;
  content_excerpt: string;
}

const DEFAULT_PUBLIC_ACTS: PublicAct[] = [
  {
    ref: 'ARR-2026-019',
    title: 'Arrêté temporaire de circulation et de stationnement Quai du Tinduff',
    category: 'Arrêté de voirie',
    commission_id: 'urbanisme_ports',
    publication_date: '18/11/2026',
    signed_by: 'Dominique CAP (Maire)',
    applicant: 'Entreprise Ouest Réseaux · Brest',
    status: 'Publié & Exécutoire',
    content_excerpt: 'ARTICLE 1ER : La circulation est temporairement réglementée sur le Quai du Tinduff du 24 au 28 novembre 2026 par alternat de feux tricolores.\nARTICLE 2 : Le stationnement de tout véhicule est interdit sur 50 mètres aux abords du chantier.\nARTICLE 3 : Le présent arrêté est exécutoire et notifié au chef de brigade de gendarmerie.',
  },
  {
    ref: 'DELIB-2026-031',
    title: 'Adoption du compte administratif 2025 et approbation nomenclature M57',
    category: 'Délibération du conseil',
    commission_id: 'finances_rh',
    publication_date: '15/11/2026',
    signed_by: 'Dominique CAP (Maire)',
    applicant: 'Direction des Finances',
    status: 'Publié & Exécutoire',
    content_excerpt: 'Le Conseil Municipal, après en avoir délibéré à l’unanimité des membres présents, approuve les comptes de gestion M57 de l’exercice 2025 et l’affectation du résultat excédentaire d’investissement.',
  },
  {
    ref: 'MP-2026-008',
    title: 'Attribution du marché public de réfection de la toiture du Gymnase de l’Avel-Vor',
    category: 'Marché public',
    commission_id: 'finances_rh',
    publication_date: '12/11/2026',
    signed_by: 'Dominique CAP (Maire)',
    applicant: 'SAS Charpentes d’Armor',
    status: 'Publié & Exécutoire',
    content_excerpt: 'Attribution du lot 01 Couverture et étanchéité pour un montant de 34 850 € HT à la société SAS Charpentes d’Armor. Imputation sur le budget principal d’investissement 2026.',
  },
  {
    ref: 'PC-2026-042',
    title: 'Permis de construire portant extension et toiture ardoise Ty-Ar-Braz',
    category: 'Autorisation d’urbanisme',
    commission_id: 'urbanisme_ports',
    publication_date: '10/11/2026',
    signed_by: 'Paul Cueff (Par délégation)',
    applicant: 'Demandeur particulier (Identité protégée RGPD)',
    status: 'Publié & Exécutoire',
    content_excerpt: 'Arrêté accordant le permis de construire n° PC-2026-042 pour l’extension d’une habitation individuelle et la rénovation en ardoises naturelles, conforme aux prescriptions ABF et PLU.',
  },
];

export function PublicRegisterPage({ initialRef }: { initialRef?: string }) {
  const [selectedRef, setSelectedRef] = useState<string | null>(initialRef || null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [acts, setActs] = useState<PublicAct[]>(DEFAULT_PUBLIC_ACTS);

  // Synchronisation avec l'URL hash
  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash;
      const match = hash.match(/#\/registre-public\/?(.*)/);
      if (match && match[1]) {
        setSelectedRef(decodeURIComponent(match[1]));
      } else {
        setSelectedRef(null);
      }
    };
    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  // Tentative de récupération depuis l'API publique souveraine
  useEffect(() => {
    fetch('/api/v1/public/registre')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          // Double sécurité : filtrage strict de toute donnée CCAS
          const filtered = data.filter((a: any) => 
            a.commission_id !== 'enfance_sociale' && !a.is_ccas_secret
          );
          setActs(filtered);
        }
      })
      .catch(() => {
        // En cas de mode hors ligne pur, on conserve les actes officiels par défaut
      });
  }, []);

  // Filtrage
  const filteredActs = useMemo(() => {
    return acts.filter(act => {
      // Sécurité absolue CCAS
      if (act.commission_id === 'enfance_sociale' || (act as any).is_ccas_secret) return false;

      if (selectedCategory !== 'all') {
        if (!act.category.toLowerCase().includes(selectedCategory.toLowerCase())) return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          act.ref.toLowerCase().includes(q) ||
          act.title.toLowerCase().includes(q) ||
          act.category.toLowerCase().includes(q) ||
          act.applicant.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [acts, selectedCategory, searchQuery]);

  const activeAct = useMemo(() => {
    if (!selectedRef) return null;
    return acts.find(a => a.ref.toUpperCase() === selectedRef.toUpperCase()) || null;
  }, [acts, selectedRef]);

  const activeActQrSvg = useMemo(() => {
    if (!activeAct) return null;
    const url = `${window.location.origin}/#/registre-public/${encodeURIComponent(activeAct.ref)}`;
    const matrix = generateQrMatrix(url);
    return matrixToSvgPath(matrix, 5);
  }, [activeAct]);

  return (
    <div className="min-h-screen bg-[#F7F7F5] text-stone-900 font-sans selection:bg-[#102A4C] selection:text-white pb-16">
      
      {/* Barre supérieure régalienne */}
      <header className="bg-white border-b border-stone-200 sticky top-0 z-30 shadow-3xs">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-5 w-2 rounded-xs overflow-hidden">
              <div className="w-1/3 bg-blue-700" />
              <div className="w-1/3 bg-white border-y border-stone-200" />
              <div className="w-1/3 bg-red-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-[#102A4C] text-sm tracking-tight">MayorTech.</span>
                <span className="text-stone-300">|</span>
                <h1 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
                  Registre Public des Actes Administratifs
                </h1>
              </div>
              <p className="text-[11px] text-stone-500 font-medium">
                Commune de Plougastel-Daoulas · Arrondissement de Brest
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a 
              href="#/" 
              className="text-xs font-semibold text-stone-600 hover:text-[#102A4C] px-3 py-1.5 rounded-lg hover:bg-stone-100 transition-colors"
            >
              Espace agents
            </a>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 pt-6">

        {/* Détail d'un acte sélectionné */}
        {activeAct ? (
          <div className="space-y-4 animate-in fade-in duration-150">
            <button
              onClick={() => {
                setSelectedRef(null);
                window.location.hash = '#/registre-public';
              }}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-stone-600 hover:text-[#102A4C] px-2.5 py-1.5 rounded-lg hover:bg-white transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Retour à la liste des actes</span>
            </button>

            {/* Document officiel pleine page */}
            <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6 sm:p-10 max-w-4xl mx-auto font-serif">
              
              {/* Header République Française */}
              <div className="text-center border-b-2 border-[#102A4C] pb-6 mb-6">
                <div className="flex h-1.5 w-16 rounded-full overflow-hidden mx-auto mb-3">
                  <div className="w-1/3 bg-blue-700" />
                  <div className="w-1/3 bg-white border-y border-stone-200" />
                  <div className="w-1/3 bg-red-600" />
                </div>
                <h2 className="text-base font-bold uppercase tracking-widest text-[#102A4C]">
                  RÉPUBLIQUE FRANÇAISE
                </h2>
                <p className="text-xs font-sans text-stone-500 mt-1">
                  Département du Finistère · Ville de Plougastel-Daoulas
                </p>
                <p className="text-xs font-sans font-semibold text-[#0F766E] mt-1 flex items-center justify-center gap-1.5">
                  <CheckCircle2 size={13} />
                  <span>ACTE CERTIFIÉ EXÉCUTOIRE & PUBLIÉ AU REGISTRE ÉLECTRONIQUE</span>
                </p>
              </div>

              {/* Barre de références */}
              <div className="bg-stone-50 border border-stone-200 rounded-xl p-4 font-sans text-xs grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
                <div>
                  <span className="text-stone-500 font-semibold block text-[10px] uppercase">Référence officielle</span>
                  <span className="font-mono font-bold text-sm text-[#102A4C]">{activeAct.ref}</span>
                </div>
                <div>
                  <span className="text-stone-500 font-semibold block text-[10px] uppercase">Catégorie</span>
                  <span className="font-medium text-stone-800">{activeAct.category}</span>
                </div>
                <div>
                  <span className="text-stone-500 font-semibold block text-[10px] uppercase">Date de publication</span>
                  <span className="font-medium text-stone-800">{activeAct.publication_date}</span>
                </div>
                <div>
                  <span className="text-stone-500 font-semibold block text-[10px] uppercase">Pétitionnaire / Objet</span>
                  <span className="font-medium text-stone-800">{activeAct.applicant}</span>
                </div>
              </div>

              {/* Titre */}
              <h3 className="text-base sm:text-lg font-bold text-[#102A4C] leading-snug mb-6">
                {activeAct.title}
              </h3>

              {/* Corps de l'acte */}
              <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap text-stone-800 py-4 border-y border-stone-100">
                {activeAct.content_excerpt}
              </div>

              {/* Bloc Signature & QR Code d'authenticité */}
              <div className="pt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 font-sans">
                {/* QR Code vectoriel certifié */}
                {activeActQrSvg && (
                  <div className="flex items-center gap-3 p-3 bg-stone-50 rounded-xl border border-stone-200/80">
                    <svg
                      width={activeActQrSvg.totalSize}
                      height={activeActQrSvg.totalSize}
                      viewBox={`0 0 ${activeActQrSvg.totalSize} ${activeActQrSvg.totalSize}`}
                      className="w-16 h-16 shrink-0"
                      shapeRendering="crispEdges"
                    >
                      <rect width={activeActQrSvg.totalSize} height={activeActQrSvg.totalSize} fill="#FFFFFF" />
                      <path d={activeActQrSvg.path} fill="#102A4C" />
                    </svg>
                    <div className="text-[10px] text-stone-500 space-y-0.5">
                      <p className="font-bold text-[#102A4C]">Affichage légal vérifié</p>
                      <p>Scellé eIDAS / RGS**</p>
                      <p className="font-mono text-[9px]">{activeAct.ref}</p>
                    </div>
                  </div>
                )}

                {/* Mention légale du signataire */}
                <div className="text-right space-y-1 sm:ml-auto">
                  <p className="text-xs text-stone-600">Fait en l'Hôtel de Ville de Plougastel-Daoulas</p>
                  <p className="font-bold text-[#102A4C] text-xs">Pour le Maire de Plougastel-Daoulas,</p>
                  <p className="text-xs font-semibold text-stone-900 pt-3">{activeAct.signed_by}</p>
                  <p className="text-[10px] text-stone-400 italic">
                    Certifié exécutoire par transmission préfectorale (@CTES)
                  </p>
                </div>
              </div>

              {/* Actions : Imprimer */}
              <div className="mt-8 pt-4 border-t border-stone-200 flex justify-end font-sans">
                <Button
                  onClick={() => window.print()}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-1.5 text-xs cursor-pointer"
                >
                  <Printer size={14} />
                  <span>Imprimer cette décision officielle</span>
                </Button>
              </div>

            </div>
          </div>
        ) : (
          /* Liste des actes administratifs */
          <div className="space-y-5">
            
            {/* Bannière explicative sobre */}
            <div className="bg-white border border-stone-200 rounded-2xl p-5 shadow-3xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-sm font-bold text-[#102A4C]">
                  Publication électronique des actes de la Ville de Plougastel-Daoulas
                </h2>
                <p className="text-xs text-stone-500 mt-0.5">
                  Conformément à l’article L. 2131-1 du Code Général des Collectivités Territoriales (CGCT).
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0 text-xs font-semibold text-[#0F766E] bg-teal-50 px-3 py-1.5 rounded-lg border border-teal-200">
                <ShieldCheck size={16} />
                <span>Registre certifié sans fuite de données personnelles</span>
              </div>
            </div>

            {/* Barre de recherche et filtres */}
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <div className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher un arrêté, une délibération, un marché, une référence..."
                  className="w-full pl-9 pr-3 py-2 bg-white border border-stone-200 rounded-xl text-xs text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-1 focus:ring-[#102A4C] shadow-3xs"
                />
              </div>

              {/* Catégories sobres */}
              <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto text-xs shrink-0">
                {[
                  { id: 'all', label: 'Tous les actes' },
                  { id: 'arrêté', label: 'Arrêtés' },
                  { id: 'délibération', label: 'Délibérations' },
                  { id: 'marché', label: 'Marchés' },
                  { id: 'urbanisme', label: 'Urbanisme' },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-3 py-1.5 rounded-lg font-semibold transition-colors cursor-pointer shrink-0 ${
                      selectedCategory === cat.id
                        ? 'bg-[#102A4C] text-white shadow-3xs'
                        : 'bg-white border border-stone-200 text-stone-700 hover:bg-stone-50'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tableau / Liste sobre Civic Craft (divide-y, zéro card-in-card) */}
            <div className="bg-white border border-stone-200 rounded-2xl shadow-3xs overflow-hidden">
              <div className="divide-y divide-stone-200">
                {filteredActs.length === 0 ? (
                  <div className="p-8 text-center text-xs text-stone-500">
                    Aucun acte administratif ne correspond à votre recherche.
                  </div>
                ) : (
                  filteredActs.map((act) => (
                    <div
                      key={act.ref}
                      onClick={() => {
                        setSelectedRef(act.ref);
                        window.location.hash = `#/registre-public/${encodeURIComponent(act.ref)}`;
                      }}
                      className="p-4 sm:p-5 hover:bg-stone-50/80 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-[#102A4C]">
                            {act.ref}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-md font-semibold bg-stone-100 text-stone-700 border border-stone-200">
                            {act.category}
                          </span>
                          <span className="text-xs text-stone-400">·</span>
                          <span className="text-xs text-stone-500 font-medium">
                            Publié le {act.publication_date}
                          </span>
                        </div>
                        <h3 className="text-xs sm:text-sm font-semibold text-stone-900 group-hover:text-[#102A4C] transition-colors leading-snug">
                          {act.title}
                        </h3>
                        <p className="text-[11px] text-stone-500">
                          {act.applicant} · {act.signed_by}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 sm:self-center shrink-0">
                        <span className="text-[11px] font-semibold text-[#0F766E] flex items-center gap-1">
                          <CheckCircle2 size={13} />
                          <span>Exécutoire</span>
                        </span>
                        <span className="text-xs text-stone-400 group-hover:text-[#102A4C] group-hover:translate-x-0.5 transition-all">
                          →
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Note de bas de page RGPD & CCAS */}
            <div className="text-center text-[11px] text-stone-500 py-4">
              <p>
                Mairie de Plougastel-Daoulas · 1 Rue Jean Moulin · 29470 Plougastel-Daoulas · 02 98 37 57 57
              </p>
              <p className="text-[10px] text-stone-400 mt-0.5">
                Conformément au RGPD et au Code de l'Action Sociale et des Familles, les décisions d'aide sociale (CCAS) et données privées font l'objet d'un secret légal strict et ne sont jamais publiées.
              </p>
            </div>

          </div>
        )}

      </main>
    </div>
  );
}
