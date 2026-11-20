import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';

export interface ModuleItem {
  key: string;
  name: string;
  description: string;
  category: 'socle' | 'metier' | 'options';
  locked: boolean;
  circuits: string[];
  icon: string;
}

export interface PresetItem {
  id: string;
  label: string;
  description: string;
  modules: string[];
}

export interface OrgMetadata {
  tenant_id: string;
  name: string;
  insee_code: string;
  stratum: string;
  email_domain: string;
}

export interface OrganizationModulesContextValue {
  modules: string[];
  organization: OrgMetadata;
  catalog: ModuleItem[];
  presets: Record<string, PresetItem>;
  hasModule: (key: string) => boolean;
  toggleModule: (key: string) => Promise<void>;
  applyPreset: (presetId: string) => Promise<void>;
  saveModules: (newModules: string[]) => Promise<void>;
  createOrganization: (data: {
    name: string;
    insee_code?: string;
    stratum?: string;
    email_domain?: string;
    enabled_modules?: string[];
  }) => Promise<any>;
  loading: boolean;
  isWizardOpen: boolean;
  setIsWizardOpen: (open: boolean) => void;
}

// Canonical static defaults for instant display & offline resilience
const DEFAULT_CATALOG: ModuleItem[] = [
  {
    key: 'core_directory',
    name: 'Annuaire & Organigramme',
    description: 'Double hiérarchie élus et administration, délégations d’arrêtés et suppléances',
    category: 'socle',
    locked: true,
    circuits: ['Tous les circuits'],
    icon: 'Users',
  },
  {
    key: 'core_workflows',
    name: 'Circuits de validation BPMN',
    description: 'Moteur de circuits BPMN 2.0, visas régaliens, signatures et journal d’audit',
    category: 'socle',
    locked: true,
    circuits: ['Moteur BPMN 2.0'],
    icon: 'GitBranch',
  },
  {
    key: 'core_documents',
    name: 'Documents & Coffre SHA-256',
    description: 'Coffre-fort d’actes scellés, pièces Cerfa et empreinte d\'intégrité SHA-256 (compatible parapheur eIDAS)',
    category: 'socle',
    locked: true,
    circuits: ['Contrôle légalité'],
    icon: 'FileCheck2',
  },
  {
    key: 'urbanisme_ads',
    name: 'Urbanisme, PLU & Cadastre',
    description: 'Instruction ADS, conformité zonage PLU, consultations ABF et avis voirie CTM',
    category: 'metier',
    locked: false,
    circuits: ['Permis de Construire (ADS)', 'Déclaration Préalable'],
    icon: 'Building',
  },
  {
    key: 'ports_littoral',
    name: 'Ports, Mouillages & Littoral',
    description: 'Gestion des cales, concessions portuaires, mouillages et autorisations domaine maritime',
    category: 'metier',
    locked: false,
    circuits: ['Autorisation d’Occupation Temporaire (AOT)'],
    icon: 'Anchor',
  },
  {
    key: 'travaux_terrain',
    name: 'Chantiers, Gantt & Suivi Terrain',
    description: 'Pilotage des arrêtés de voirie, chantiers municipaux et interventions des équipes CTM',
    category: 'metier',
    locked: false,
    circuits: ['Arrêté de Voirie & Police', 'Intervention CTM'],
    icon: 'HardHat',
  },
  {
    key: 'enfance_ccas',
    name: 'Enfance, Scolaire, QF & CCAS',
    description: 'Inscriptions scolaires, quotient familial CAF, restauration scolaire et aides sociales',
    category: 'metier',
    locked: false,
    circuits: ['Aide Sociale CCAS', 'Dérogation Scolaire'],
    icon: 'GraduationCap',
  },
  {
    key: 'finances_m57',
    name: 'Finances M57 & Marchés Publics',
    description: 'Engagements budgétaires M57, seuils CAO et commissions d’appel d’offres',
    category: 'metier',
    locked: false,
    circuits: ['Marché Public (CAO)', 'Subvention Municipale'],
    icon: 'Coins',
  },
  {
    key: 'conseil_seances',
    name: 'Séances du Conseil & Délibérations',
    description: 'Ordre du jour, gestion des présences/quorum, et télétransmission des délibérations',
    category: 'metier',
    locked: false,
    circuits: ['Délibération du Conseil'],
    icon: 'Landmark',
  },
  {
    key: 'messagerie_eml',
    name: 'Messagerie & Archives EML',
    description: 'Collecte, tri et archivage des courriels citoyens et échanges administratifs',
    category: 'metier',
    locked: false,
    circuits: ['Signalement Courriel'],
    icon: 'Mail',
  },
  {
    key: 'ai_assistant',
    name: 'Assistant IA & Prompt-to-BPMN',
    description: 'Génération automatique de processus BPMN 2.0 et assistance à la rédaction d’arrêtés',
    category: 'options',
    locked: false,
    circuits: ['Studio IA'],
    icon: 'MessageSquare',
  },
  {
    key: 'connector_ctes',
    name: 'Télétransmission @CTES / Pastell',
    description: 'Liaison directe avec le contrôle de légalité en Préfecture et bordereaux d’acquittement',
    category: 'options',
    locked: false,
    circuits: ['Télétransmission Préfecture'],
    icon: 'Send',
  },
  {
    key: 'connector_eidas',
    name: 'Parapheur eIDAS / RGS**',
    description: 'Délégation de signature qualifiée avec certificat cryptographique matériel du Maire',
    category: 'options',
    locked: false,
    circuits: ['Signature RGS**'],
    icon: 'ShieldCheck',
  },
  {
    key: 'mobile_alerts',
    name: 'Alertes mobiles terrain souveraines',
    description: 'Notifications push Ntfy temps réel pour les agents de voirie et alertes SLA 24h',
    category: 'options',
    locked: false,
    circuits: ['Alerte SLA SMS/Push'],
    icon: 'Smartphone',
  },
];

const DEFAULT_PRESETS: Record<string, PresetItem> = {
  iterop_pure: {
    id: 'iterop_pure',
    label: 'Circuits seuls',
    description: 'Socle uniquement : circuits de validation, documents et coffre certifié',
    modules: ['core_directory', 'core_workflows', 'core_documents'],
  },
  commune_rurale: {
    id: 'commune_rurale',
    label: 'Commune rurale',
    description: 'Socle + Travaux & Voirie + Conseil Municipal + Messagerie',
    modules: [
      'core_directory',
      'core_workflows',
      'core_documents',
      'travaux_terrain',
      'conseil_seances',
      'messagerie_eml',
      'mobile_alerts',
    ],
  },
  ville_complete: {
    id: 'ville_complete',
    label: 'Ville complète',
    description: 'Tous les services et options activés, sauf Ports & Littoral',
    modules: [
      'core_directory',
      'core_workflows',
      'core_documents',
      'urbanisme_ads',
      'travaux_terrain',
      'enfance_ccas',
      'finances_m57',
      'conseil_seances',
      'messagerie_eml',
      'ai_assistant',
      'connector_ctes',
      'connector_eidas',
      'mobile_alerts',
    ],
  },
  commune_littorale: {
    id: 'commune_littorale',
    label: 'Commune littorale',
    description: 'Tous les modules activés (y compris Ports, Mouillages & Littoral)',
    modules: DEFAULT_CATALOG.map((m) => m.key),
  },
};

const ALL_KEYS = DEFAULT_CATALOG.map((m) => m.key);
const STORAGE_KEY = 'mayortech_active_modules';
const STORAGE_ORG_KEY = 'mayortech_active_org_metadata';

const OrganizationModulesContext = createContext<OrganizationModulesContextValue | null>(null);

export function OrganizationModulesProvider({ children }: { children: React.ReactNode }) {
  const [modules, setModules] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return ALL_KEYS;
  });

  const [organization, setOrganization] = useState<OrgMetadata>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_ORG_KEY);
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return {
      tenant_id: 'plougastel-daoulas',
      name: 'Ville de Plougastel-Daoulas',
      insee_code: '29189',
      stratum: '3500-15000',
      email_domain: 'plougastel.fr',
    };
  });

  const [catalog, setCatalog] = useState<ModuleItem[]>(DEFAULT_CATALOG);
  const [presets, setPresets] = useState<Record<string, PresetItem>>(DEFAULT_PRESETS);
  const [loading, setLoading] = useState(false);
  const [isWizardOpen, setIsWizardOpen] = useState(false);

  // Sync with backend on startup
  useEffect(() => {
    let active = true;
    async function fetchModules() {
      try {
        const res = await fetch('/api/v1/organizations/current/modules', {
          headers: { 'X-Requested-With': 'Travaux' },
        });
        if (res.ok) {
          const data = await res.json();
          if (active) {
            if (Array.isArray(data.enabled_modules)) {
              setModules(data.enabled_modules);
              localStorage.setItem(STORAGE_KEY, JSON.stringify(data.enabled_modules));
            }
            if (data.catalog) setCatalog(data.catalog);
            if (data.presets) setPresets(data.presets);
            setOrganization({
              tenant_id: data.tenant_id || 'plougastel-daoulas',
              name: data.name || 'Ville de Plougastel-Daoulas',
              insee_code: data.insee_code || '29189',
              stratum: data.stratum || '3500-15000',
              email_domain: data.email_domain || 'plougastel.fr',
            });
          }
        }
      } catch (err) {
        // Fallback silently to local state
      }
    }
    fetchModules();
    return () => {
      active = false;
    };
  }, []);

  const hasModule = useCallback(
    (key: string) => {
      const item = catalog.find((m) => m.key === key);
      if (item?.locked) return true;
      return modules.includes(key);
    },
    [modules, catalog]
  );

  const saveModules = useCallback(
    async (newModules: string[]) => {
      // Always include locked modules
      const locked = catalog.filter((m) => m.locked).map((m) => m.key);
      const unified = Array.from(new Set([...newModules, ...locked]));

      setModules(unified);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(unified));
      } catch (_) {}

      try {
        await fetch('/api/v1/organizations/current/modules', {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'Travaux',
          },
          body: JSON.stringify({ enabled_modules: unified }),
        });
      } catch (e) {
        // Local persistence ensures instant UI reaction
      }
    },
    [catalog]
  );

  const toggleModule = useCallback(
    async (key: string) => {
      const item = catalog.find((m) => m.key === key);
      if (item?.locked) {
        toast.info(`Le module "${item.name}" fait partie du socle régalien obligatoire.`);
        return;
      }

      const active = modules.includes(key);
      const next = active ? modules.filter((k) => k !== key) : [...modules, key];
      await saveModules(next);

      if (active) {
        toast.info(`Module "${item?.name || key}" masqué (données et historique conservés).`);
      } else {
        toast.success(`Module "${item?.name || key}" activé avec succès !`);
      }
    },
    [modules, catalog, saveModules]
  );

  const applyPreset = useCallback(
    async (presetId: string) => {
      const p = presets[presetId] || DEFAULT_PRESETS[presetId];
      if (!p) return;
      await saveModules(p.modules);
      toast.success(`Profil "${p.label}" appliqué (${p.modules.length} modules actifs)`);
    },
    [presets, saveModules]
  );

  const createOrganization = useCallback(
    async (data: {
      name: string;
      insee_code?: string;
      stratum?: string;
      email_domain?: string;
      enabled_modules?: string[];
    }) => {
      setLoading(true);
      try {
        const unified = Array.from(
          new Set([...(data.enabled_modules || ALL_KEYS), 'core_directory', 'core_workflows', 'core_documents'])
        );
        const res = await fetch('/api/v1/organizations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'Travaux',
          },
          body: JSON.stringify({
            name: data.name,
            insee_code: data.insee_code || '',
            stratum: data.stratum || '3500-15000',
            email_domain: data.email_domain || '',
            enabled_modules: unified,
          }),
        });

        let resultData: any;
        if (res.ok) {
          resultData = await res.json();
        } else {
          resultData = {
            tenant_id: `org-${Date.now()}`,
            name: data.name,
            insee_code: data.insee_code || '',
            stratum: data.stratum || '3500-15000',
            email_domain: data.email_domain || '',
            enabled_modules: unified,
          };
        }

        setModules(unified);
        setOrganization({
          tenant_id: resultData.tenant_id,
          name: resultData.name,
          insee_code: resultData.insee_code,
          stratum: resultData.stratum,
          email_domain: resultData.email_domain,
        });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(unified));
        localStorage.setItem(
          STORAGE_ORG_KEY,
          JSON.stringify({
            tenant_id: resultData.tenant_id,
            name: resultData.name,
            insee_code: resultData.insee_code,
            stratum: resultData.stratum,
            email_domain: resultData.email_domain,
          })
        );

        toast.success(`Collectivité "${data.name}" initialisée avec succès !`);
        return resultData;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return (
    <OrganizationModulesContext.Provider
      value={{
        modules,
        organization,
        catalog,
        presets,
        hasModule,
        toggleModule,
        applyPreset,
        saveModules,
        createOrganization,
        loading,
        isWizardOpen,
        setIsWizardOpen,
      }}
    >
      {children}
    </OrganizationModulesContext.Provider>
  );
}

export function useOrganizationModules() {
  const ctx = useContext(OrganizationModulesContext);
  if (!ctx) {
    throw new Error('useOrganizationModules must be used within an OrganizationModulesProvider');
  }
  return ctx;
}
