/**
 * Utilitaire de comparaison mot-à-mot (Diff) pour les actes juridiques municipaux.
 * Implémentation déterministe basée sur le Plus Long Sous-Ensemble Commun (LCS).
 * Zéro dépendance externe, typographie éditoriale Civic Craft.
 */

export interface DiffPart {
  type: 'added' | 'removed' | 'unchanged';
  value: string;
}

export interface DiffSummary {
  parts: DiffPart[];
  additionsCount: number;
  deletionsCount: number;
  hasChanges: boolean;
}

/**
 * Découpe un texte en jetons (mots, espaces et ponctuation).
 */
function tokenize(text: string): string[] {
  if (!text) return [];
  // Découpe en gardant les espaces et la ponctuation pour préserver la mise en page
  const matches = text.match(/([A-Za-zÀ-ÖØ-öø-ÿ0-9'’-]+|\s+|[.,;:"«»!?()\[\]\/\\–—-])/g);
  return matches || [text];
}

/**
 * Calcule le diff mot-à-mot entre deux versions d'un texte d'acte.
 */
export function computeWordDiff(oldText: string, newText: string): DiffSummary {
  if (oldText === newText) {
    return {
      parts: [{ type: 'unchanged', value: newText }],
      additionsCount: 0,
      deletionsCount: 0,
      hasChanges: false,
    };
  }

  const tokensA = tokenize(oldText);
  const tokensB = tokenize(newText);
  const n = tokensA.length;
  const m = tokensB.length;

  // Matrice LCS (Longest Common Subsequence)
  // Utilisation de tableaux typés pour une vitesse d'exécution optimale
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < m; j++) {
      if (tokensA[i] === tokensB[j]) {
        dp[i + 1][j + 1] = dp[i][j] + 1;
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }

  // Remontée pour construire la séquence de diff
  const rawParts: DiffPart[] = [];
  let i = n;
  let j = m;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && tokensA[i - 1] === tokensB[j - 1]) {
      rawParts.push({ type: 'unchanged', value: tokensA[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      rawParts.push({ type: 'added', value: tokensB[j - 1] });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      rawParts.push({ type: 'removed', value: tokensA[i - 1] });
      i--;
    }
  }

  rawParts.reverse();

  // Fusionner les morceaux contigus de même type
  const merged: DiffPart[] = [];
  let additionsCount = 0;
  let deletionsCount = 0;

  for (const part of rawParts) {
    // Compter les mots réels (ignorer les espaces purs dans le comptage statistique)
    const isWord = /[A-Za-zÀ-ÖØ-öø-ÿ0-9]/.test(part.value);

    if (part.type === 'added' && isWord) additionsCount++;
    if (part.type === 'removed' && isWord) deletionsCount++;

    if (merged.length > 0 && merged[merged.length - 1].type === part.type) {
      merged[merged.length - 1].value += part.value;
    } else {
      merged.push({ ...part });
    }
  }

  return {
    parts: merged,
    additionsCount,
    deletionsCount,
    hasChanges: additionsCount > 0 || deletionsCount > 0,
  };
}
