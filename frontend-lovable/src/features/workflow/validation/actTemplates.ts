/**
 * Gabarits juridiques à variables & seuils de délégation pour MayorTech.
 * Respecte Civic Craft & la règle Zéro Ressaisie.
 */

export interface ActTemplateVariable {
  key: string;
  label: string;
  placeholder: string;
  defaultValue: string;
  type?: 'text' | 'number' | 'date';
}

export interface ActTemplate {
  id: 'arrete' | 'deliberation' | 'marche' | 'permis';
  title: string;
  commission: string;
  category: string;
  hasFinancialThreshold: boolean;
  variables: ActTemplateVariable[];
  bodyTemplate: string;
}

export const ACT_TEMPLATES: Record<string, ActTemplate> = {
  arrete: {
    id: 'arrete',
    title: 'Arrêté temporaire de voirie',
    commission: 'Travaux & Urbanisme',
    category: 'Arrêté de voirie & police',
    hasFinancialThreshold: false,
    variables: [
      { key: 'numero_arrete', label: 'Numéro arrêté', placeholder: 'ARR-2026-022', defaultValue: 'ARR-2026-022' },
      { key: 'demandeur', label: 'Demandeur / Entreprise', placeholder: 'Entreprise Ouest Réseaux', defaultValue: 'Entreprise Ouest Réseaux · Brest' },
      { key: 'voie', label: 'Voie communale concernée', placeholder: 'Rue de Pen ar Men', defaultValue: 'Rue de Pen ar Men' },
      { key: 'date_debut', label: 'Date de début', placeholder: '25/11/2026', defaultValue: '25/11/2026', type: 'text' },
      { key: 'date_fin', label: 'Date de fin', placeholder: '02/12/2026', defaultValue: '02/12/2026', type: 'text' },
      { key: 'nature_travaux', label: 'Nature des travaux', placeholder: 'Pose de fourreaux télécoms', defaultValue: 'Tranchée sous trottoir pour raccordement fibre optique et enfouissement réseaux' },
    ],
    bodyTemplate: `ARTICLE 1ER : Du {{date_debut}} au {{date_fin}} inclus, la circulation et le stationnement sur {{voie}} sont temporairement réglementés en raison des travaux de « {{nature_travaux}} » diligentés par {{demandeur}}.

ARTICLE 2 : Un alternat de circulation par feux tricolores est mis en place par l'entreprise adjudicataire. La vitesse maximale autorisée est abaissée à 30 km/h aux abords immédiats du chantier.

ARTICLE 3 : Le présent arrêté est certifié exécutoire par le Maire de Plougastel-Daoulas, publié au registre public des actes administratifs et notifié au chef de brigade de gendarmerie.`,
  },

  deliberation: {
    id: 'deliberation',
    title: 'Délibération budgétaire M57',
    commission: 'Finances & RH',
    category: 'Délibération du conseil municipal',
    hasFinancialThreshold: true,
    variables: [
      { key: 'numero_delib', label: 'Réf. délibération', placeholder: 'DELIB-2026-035', defaultValue: 'DELIB-2026-035' },
      { key: 'objet', label: 'Objet de la délibération', placeholder: 'Affectation du résultat budgétaire M57', defaultValue: 'Approbation du compte de gestion M57 et affectation de l’excédent d’investissement' },
      { key: 'montant_ht', label: 'Montant (€ HT)', placeholder: '25000', defaultValue: '25000', type: 'number' },
      { key: 'imputation_budgetaire', label: 'Imputation M57', placeholder: 'Chapitre 021 / Article 21318', defaultValue: 'Chapitre 021 / Article 21318 · Travaux bâtiments publics' },
      { key: 'commission', label: 'Commission saisie', placeholder: 'Commission Finances & RH', defaultValue: 'Commission des Finances et des Moyens Généraux' },
    ],
    bodyTemplate: `Le Conseil Municipal de la Ville de Plougastel-Daoulas, légalement convoqué sous la présidence de Dominique CAP, Maire ;

VU le Code Général des Collectivités Territoriales et l'instruction budgétaire et comptable M57 ;
VU l'avis favorable émis par la {{commission}} ;
CONSIDÉRANT l'objet : « {{objet}} » pour un engagement financier de {{montant_ht}} € HT ;

DÉCIDE À L'UNANIMITÉ DES MEMBRES PRÉSENTS :
ARTICLE 1ER : D'approuver l'opération financière visée pour un montant total de {{montant_ht}} € HT.
ARTICLE 2 : Les crédits sont prévus et imputés sur l'exercice budgétaire 2026 selon la ventilation : {{imputation_budgetaire}}.
ARTICLE 3 : Le Maire certifie sous sa responsabilité le caractère exécutoire du présent acte, télétransmis au contrôle de légalité en Préfecture du Finistère.`,
  },

  marche: {
    id: 'marche',
    title: 'Attribution Marché Public',
    commission: 'Finances & Marchés',
    category: 'Marché public & engagement',
    hasFinancialThreshold: true,
    variables: [
      { key: 'numero_marche', label: 'Numéro de marché', placeholder: 'MP-2026-009', defaultValue: 'MP-2026-009' },
      { key: 'titulaire', label: 'Entreprise attributaire', placeholder: 'SAS Armor Toiture & Façade', defaultValue: 'SAS Ouest Charpentes & Énergie · Quimper' },
      { key: 'montant_ht', label: 'Montant (€ HT)', placeholder: '38500', defaultValue: '38500', type: 'number' },
      { key: 'lot', label: 'Lot et objet de prestation', placeholder: 'Lot 01 · Réfection de charpente', defaultValue: 'Lot 01 · Restauration des façades et étanchéité de l’espace culturel Avel-Vor' },
      { key: 'delai_execution', label: 'Délai d’exécution', placeholder: '90 jours calendaires', defaultValue: '90 jours calendaires à compter de l’ordre de service' },
    ],
    bodyTemplate: `ARTICLE 1ER : Le marché public {{numero_marche}} relatif à « {{lot}} » est attribué à la société {{titulaire}} pour un montant de {{montant_ht}} € HT.

ARTICLE 2 : Les prestations devront être exécutées dans un délai de {{delai_execution}}, conformément au Cahier des Clauses Techniques Particulières (CCTP).

ARTICLE 3 : La dépense sera imputée sur les crédits d’investissement du budget principal communal. Le présent arrêté d’attribution est notifié à l’entreprise attributaire et au représentant de l’État.`,
  },

  permis: {
    id: 'permis',
    title: 'Permis de Construire (ADS)',
    commission: 'Urbanisme & Cadre de vie',
    category: 'Autorisation d’urbanisme',
    hasFinancialThreshold: false,
    variables: [
      { key: 'numero_dossier', label: 'Numéro ADS / Cerfa', placeholder: 'PC-2026-048', defaultValue: 'PC-2026-048' },
      { key: 'demandeur', label: 'Pétitionnaire', placeholder: 'M. & Mme Jean-Luc QUÉRÉ', defaultValue: 'M. & Mme Jean-Luc QUÉRÉ' },
      { key: 'parcelle', label: 'Référence cadastrale', placeholder: 'Section AC n° 142', defaultValue: 'Cadastre Section AC n° 142 · 18 Route de l’Auberlac’h' },
      { key: 'surface_plancher', label: 'Surface de plancher', placeholder: '128 m²', defaultValue: '128 m² de surface de plancher créée' },
      { key: 'destination', label: 'Destination du projet', placeholder: 'Extension d’habitation individuelle', defaultValue: 'Extension d’habitation individuelle avec toiture ardoise naturelle et bardage bois' },
    ],
    bodyTemplate: `ARTICLE 1ER : Le permis de construire numéro {{numero_dossier}} est ACCORDÉ à {{demandeur}} pour le projet situé sur la parcelle {{parcelle}}, portant sur {{destination}} (création de {{surface_plancher}}).

ARTICLE 2 : Le demandeur devra se conformer aux prescriptions du Plan Local d’Urbanisme (PLU) en zone Ub et recueillir l'accord du gestionnaire de voirie pour le branchement des eaux pluviales.

ARTICLE 3 : Le présent arrêté sera affiché en mairie et sur le terrain d’assiette dès réception. Il devient exécutoire à compter de sa transmission en Préfecture et de son affichage réglementaire.`,
  },
};

/**
 * Remplace les variables {{key}} dans le texte par leurs valeurs effectives.
 */
export function renderTemplateText(templateText: string, variables: Record<string, string>): string {
  let result = templateText;
  for (const [key, val] of Object.entries(variables)) {
    const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
    result = result.replace(regex, val || `[${key}]`);
  }
  return result;
}

/**
 * Évalue la règle de délégation active selon le type d'acte et le montant HT.
 * Seuil pivot : 10 000 € HT.
 */
export function evaluateFinancialThreshold(circuitType: string, amountHt?: number): {
  requiresMayor: boolean;
  ruleLabel: string;
  isOverThreshold: boolean;
} {
  const threshold = 10000;
  if (amountHt === undefined || isNaN(amountHt)) {
    return {
      requiresMayor: circuitType === 'deliberation' || circuitType === 'permis',
      ruleLabel: 'Délégation permanente de signature applicable',
      isOverThreshold: false,
    };
  }

  const isOver = amountHt > threshold;
  return {
    requiresMayor: isOver,
    isOverThreshold: isOver,
    ruleLabel: isOver
      ? 'Seuil > 10 000 € HT · Escalade automatique vers le Maire requise'
      : 'Seuil ≤ 10 000 € HT · Visa DGS ou Adjoint délégataire suffisant',
  };
}
