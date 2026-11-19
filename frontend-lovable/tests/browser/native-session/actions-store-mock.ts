/** Explicit projection/transport double only for the production Actions screen. */
export function cachedNativeActions(ids:string[]){return ((window as any).__actionFixtureRows||[]).filter((item:any)=>ids.includes(item.projectId));}
export async function loadNativeActions(){if((window as any).__failActionLoad)throw Error('Échec réseau fictif pendant le rechargement des actions');}
export async function changeNativeAction(){throw Error('Mutation d’action non utilisée dans cette recette');}
export async function createNativeAction(){throw Error('Création d’action non utilisée dans cette recette');}
export async function flushNativeActions(){}
