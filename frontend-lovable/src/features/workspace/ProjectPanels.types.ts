export type ObjectValue = Record<string, unknown>;
export const objectOf = (value: unknown): ObjectValue => value && typeof value === 'object' && !Array.isArray(value) ? value as ObjectValue : {};
export const textOf = (value: unknown) => typeof value === 'string' ? value : '';
export const arrayOf = (value: unknown): unknown[] => Array.isArray(value) ? value : [];
export const resultItems = (value: unknown) => Array.isArray(value) ? value : arrayOf(objectOf(value)['items']);
const strings = (value: unknown) => arrayOf(value).filter((item): item is string => typeof item === 'string');

export interface Evidence {source_id: string; quote: string; source_hash: string; start: number | null; end: number | null}
export interface SourceRecord {id: string; subject: string; body: string; body_hash: string; sender: string; received_at: string; created_at: string; version: number; metadata: ObjectValue; project_ids: string[]}
export interface CandidateRecord {id: string; field: string; label: string; kind: string; value: unknown; status: string; origin: string; source_id: string; created_at: string; evidence: Evidence[]; conflict_with: string[]; previous_values: CandidateRecord[]; source: SourceRecord | null}
export interface NoteRecord {id: string; content: string; actor_id: string; created_at: string; source_id: string; origin: string}
export interface EventRecord {id: string; event_type: string; actor_id: string; created_at: string; revision: number; payload: ObjectValue}
export interface SummaryRecord {id: string; project_id: string; project_name: string; version: number; status: string; content: string; content_hash: string; snapshot_hash: string; snapshot_revision: number; stale: boolean; coverage_stale: boolean; coverage: string; warnings: string[]; created_at: string; approved_at: string; approved_by: string; model: string; citations: Evidence[]}
export interface DocumentRecord {id: string | null; filename: string; kind: string; source_id: string; parent_source_id: string; preview_source_id: string; sha256: string; media_type: string; available: boolean; text_available: boolean; size: number | null; created_at: string; extraction_status: string; warnings: string[]}
export interface ProjectRecord {id: string; name: string; reference: string; description: string; status: string; revision: number; properties?: {values:ObjectValue;origins:ObjectValue}; facts: CandidateRecord[]; actions: CandidateRecord[]; pending: CandidateRecord[]; notes: NoteRecord[]; sources: SourceRecord[]; events: EventRecord[]; summaries: SummaryRecord[];history_candidates:CandidateRecord[]}
export interface ProjectApi {
  project(id: string): Promise<unknown>; documents(id: string): Promise<unknown>; reviews(id?: string): Promise<unknown>;
  decide(id: string, body: {decision: 'accept' | 'replace' | 'reject'; expected_revision: number; reason?: string; corrected_value?: string}): Promise<unknown>;
  nativePage(id: string): Promise<unknown>; source(id: string): Promise<unknown>;
  summary(id: string): Promise<unknown>; generate(id: string, body: Record<string, never>): Promise<unknown>;
  saveSummary(id: string, body: {content: string; expected_content_hash: string}): Promise<unknown>;
  approve(id: string, body: {expected_content_hash: string; expected_snapshot_hash: string; expected_project_revision: number}): Promise<unknown>;
  exportUrl(id: string, format?: string): string;
  assistant(id:string,body:{question:string}):Promise<unknown>;
}
export interface NativeMetadata {managedActionDatabaseId: string | null; activeDatabaseId: string | null; databases: {id: string; title: string; managedActions: boolean; rows: {id: string; sourceKey?: string; sourceUrl?: string; fields: {id: string; name: string; type: string; text: string}[]}[]}[]}

export const fieldLabels: Record<string, string> = {deadline:'Échéance',delivery_date:'Livraison',acceptance_date:'Réception',budget_raw:'Budget',progress:'Avancement',decision:'Décision',contractor:'Entreprise',location:'Lieu',owner:'Responsable'};
export const fieldLabel = (field: string) => field.startsWith('action.') ? 'Action' : fieldLabels[field] || field;
export function evidenceOf(value: unknown): Evidence {
  const v=objectOf(value);return {source_id:textOf(v['source_id']),quote:textOf(v['quote']),source_hash:textOf(v['source_hash']),start:typeof v['start']==='number'?v['start']:null,end:typeof v['end']==='number'?v['end']:null};
}
export function sourceOf(value: unknown): SourceRecord {
  const v=objectOf(value);return {id:textOf(v['id']),subject:textOf(v['subject']),body:textOf(v['body']),body_hash:textOf(v['body_hash']),sender:textOf(v['sender']),received_at:textOf(v['received_at']),created_at:textOf(v['created_at']),version:Number(v['version'])||1,metadata:objectOf(v['metadata']),project_ids:strings(v['project_ids'])};
}
export function candidateOf(value: unknown): CandidateRecord {
  const v=objectOf(value),field=textOf(v['field']);return {id:textOf(v['id']),field,label:textOf(v['label'])||fieldLabel(field),kind:textOf(v['kind']),value:v['value'],status:textOf(v['status']),origin:textOf(v['origin']),source_id:textOf(v['source_id']),created_at:textOf(v['created_at']),evidence:arrayOf(v['evidence']).map(evidenceOf),conflict_with:strings(v['conflict_with']),previous_values:arrayOf(v['previous_values']).map(previous=>candidateOf({...objectOf(previous),previous_values:[]})),source:v['source']?sourceOf(v['source']):null};
}
export function summaryOf(value: unknown): SummaryRecord {
  const v=objectOf(value);return {id:textOf(v['id']),project_id:textOf(v['project_id']),project_name:textOf(v['project_name']),version:Number(v['version'])||1,status:textOf(v['status']),content:textOf(v['content']),content_hash:textOf(v['content_hash']),snapshot_hash:textOf(v['snapshot_hash']),snapshot_revision:Number(v['snapshot_revision']??v['project_revision'])||0,stale:v['stale']===true,coverage_stale:v['coverage_stale']===true,coverage:textOf(v['coverage']),warnings:strings(v['warnings']),created_at:textOf(v['created_at']),approved_at:textOf(v['approved_at']),approved_by:textOf(v['approved_by']),model:textOf(v['model']),citations:arrayOf(v['citations']).map(evidenceOf)};
}
export function documentOf(value: unknown): DocumentRecord {
  const v=objectOf(value);return {id:textOf(v['id'])||null,filename:textOf(v['original_filename'])||textOf(v['filename'])||'Document sans nom',kind:textOf(v['kind']),source_id:textOf(v['source_id']),parent_source_id:textOf(v['parent_source_id']),preview_source_id:textOf(v['preview_source_id']),sha256:textOf(v['sha256']),media_type:textOf(v['media_type']),available:v['available']===true,text_available:v['text_available']===true,size:typeof v['size']==='number'?v['size']:null,created_at:textOf(v['created_at']),extraction_status:textOf(v['extraction_status']),warnings:strings(v['warnings'])};
}
export function projectOf(value: unknown): ProjectRecord {
  const v=objectOf(value),p={...objectOf(v['project']),...v},id=textOf(p['id']);
  if(!id||!Number.isSafeInteger(p['revision']))throw new Error('Le dossier reçu est incomplet. Rechargez-le pour consulter ses informations.');
  const facts=arrayOf(p['facts']).map(candidateOf).filter(item=>item.status==='accepted');
  return {id,name:textOf(p['name']),reference:textOf(p['reference']),description:textOf(p['description']),status:textOf(p['status']),revision:p['revision'] as number,properties:{values:objectOf(objectOf(p['properties'])['values']),origins:objectOf(objectOf(p['properties'])['origins'])},facts,history_candidates:arrayOf(p['history_candidates']).map(candidateOf),actions:facts.filter(item=>item.field.startsWith('action.')),pending:arrayOf(p['pending']).map(candidateOf).filter(item=>item.status==='pending'),notes:arrayOf(p['notes']).map(note=>{const n=objectOf(note);return {id:textOf(n['id']),content:textOf(n['content']),actor_id:textOf(n['actor_id']),created_at:textOf(n['created_at']),source_id:textOf(n['source_id']),origin:textOf(n['origin'])};}),sources:arrayOf(p['sources']).map(sourceOf),events:arrayOf(p['events']).map(event=>{const e=objectOf(event);return {id:textOf(e['id']),event_type:textOf(e['event_type']),actor_id:textOf(e['actor_id']),created_at:textOf(e['created_at']),revision:Number(e['revision'])||0,payload:objectOf(e['payload'])};}),summaries:arrayOf(p['summaries']).map(summaryOf)};
}

/** A note save may advance the revision; unseen facts/proposals still require review. */
export function sameReviewContext(before:ProjectRecord,after:ProjectRecord){
  const snapshot=(project:ProjectRecord)=>JSON.stringify({facts:project.facts.map(({id,field,value,source_id})=>({id,field,value,source_id})).sort((a,b)=>a.id.localeCompare(b.id)),pending:project.pending.map(({id,field,value,source_id})=>({id,field,value,source_id})).sort((a,b)=>a.id.localeCompare(b.id))});
  return before.id===after.id&&snapshot(before)===snapshot(after);
}
