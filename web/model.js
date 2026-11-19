import {sanitizeHttpUrl} from './upstream-grist.js';

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
}

export function safeUrl(value) {
  if (!value || typeof value !== 'string') return '';
  return sanitizeHttpUrl(value) || '';
}

const statuses = {
  proposed:'À vérifier', pending:'À vérifier', accepted:'Confirmé', validated:'Validé', confirmed:'Confirmé',
  rejected:'Écarté', corrected:'Corrigé', contradiction:'Contradiction', conflict:'Conflit',
  draft:'Brouillon', needs_review:'À relire', approved:'Validé', stale:'À actualiser', superseded:'Version précédente',
  in_progress:'En cours', active:'En cours', planned:'En préparation', on_hold:'En attente', completed:'Terminé', closed:'Terminé',
  open:'À faire', done:'Terminé', cancelled:'Annulé', blocked:'Bloqué', ready:'Prêt',
  connected:'Connecté', disconnected:'Non connecté', not_configured:'À configurer', disabled:'Désactivé',
  demo:'Démonstration', fake:'Mode déterministe', local:'Local', partial:'Partiel', failed:'Échec',
  succeeded:'Traité', processed:'Traité', imported:'Importé', extracted:'Analysé', needs_match:'Chantier à préciser', manual:'Note humaine', configured:'Configuré', unmatched:'À rattacher', ambiguous:'Plusieurs chantiers', unavailable:'Indisponible', unverified:'Non vérifié'
};
export function statusLabel(status) { return statuses[status] || String(status || 'Non renseigné'); }
export function statusTone(status) {
  if (['accepted','validated','confirmed','approved','ready','connected','done','completed','succeeded','processed','imported'].includes(status)) return 'positive';
  if (['rejected','failed','blocked','contradiction','conflict','unavailable'].includes(status)) return 'danger';
  if (['proposed','pending','partial','stale','unverified'].includes(status)) return 'warning';
  return 'neutral';
}
export function displayValue(value) {
  if (value === null || value === undefined || value === '') return 'Non renseigné';
  if (typeof value === 'object') {
    if (value.amount !== undefined) return [value.amount,value.currency,value.tax_basis??value.basis].filter(v=>v!==undefined&&v!==null&&v!=='').join(' ');
    if (value.value !== undefined) return displayValue(value.value);
    return JSON.stringify(value);
  }
  return String(value);
}
export function dateLabel(value, withTime = false) {
  if (!value) return 'Non renseignée';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',day:'numeric',month:'short',year:'numeric',...(withTime?{hour:'2-digit',minute:'2-digit'}:{})}).format(parsed);
}
export function canApprove(summary) {
  return Boolean(summary && !summary.stale && !summary.coverage_stale && ['draft','review','needs_review','ready','pending_review'].includes(summary.status) && String(summary.content || '').trim() && summary.content_hash && summary.snapshot_hash && (summary.project_revision??summary.snapshot_revision) !== null && (summary.project_revision??summary.snapshot_revision) !== undefined);
}
export function listOf(value, key = 'items') {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.[key])) return value[key];
  for (const name of ['items','projects','reviews','candidates','summaries','imports','sources','actions']) if (Array.isArray(value?.[name])) return value[name];
  return [];
}
export function projectTitle(project) { return project?.name || project?.title || project?.reference || 'Chantier sans nom'; }

export function projectPendingCount(project) {
  return Math.max(0,Number(project.pending_reviews ?? project.pending_count ?? project.proposals_count ?? 0)||0);
}
export function prioritizeProjects(projects) {
  return [...projects].sort((a,b)=>
    Number(projectPendingCount(b)>0)-Number(projectPendingCount(a)>0) ||
    (Number(b.conflict_count)||0)-(Number(a.conflict_count)||0) ||
    String(b.updated_at||b.last_updated||b.created_at||'').localeCompare(String(a.updated_at||a.last_updated||a.created_at||'')) ||
    String(a.reference||projectTitle(a)).localeCompare(String(b.reference||projectTitle(b)),'fr')
  );
}
export function filterProjects(projects,{term='',status=''}={}) {
  const search=String(term).toLocaleLowerCase('fr').trim();
  const normalized=status==='closed'?'completed':status;
  const matches=project=>!normalized || (normalized==='completed'?['completed','closed'].includes(project.status):normalized==='active'?['active','in_progress'].includes(project.status):project.status===normalized);
  return prioritizeProjects(projects.filter(project=>matches(project)&&[projectTitle(project),project.location,project.reference].join(' ').toLocaleLowerCase('fr').includes(search)));
}

