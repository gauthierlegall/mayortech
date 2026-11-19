import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from '../../../node_modules/typescript/lib/typescript.js';

async function sourceModule(name){
  const source=await readFile(new URL(name,import.meta.url),'utf8');
  const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,'+Buffer.from(output).toString('base64'));
}
const {registerPreserver,preservePanels,hasDirtyPanels}=await sourceModule('./panel-lifecycle.ts');
const {projectOf,documentOf,summaryOf,candidateOf,sameReviewContext}=await sourceModule('./ProjectPanels.types.ts');

test('navigation waits for actual controllers and unregisters cleanly',async()=>{
  const events=[],remove=registerPreserver(async()=>{await Promise.resolve();events.push('saved');},()=>true);
  assert.equal(hasDirtyPanels(),true);await preservePanels();events.push('navigation');
  assert.deepEqual(events,['saved','navigation']);remove();assert.equal(hasDirtyPanels(),false);
});
test('conflict stops navigation without poisoning the next save attempt',async()=>{
  let conflict=true;const remove=registerPreserver(async()=>{if(conflict)throw Error('revision_conflict');});
  await assert.rejects(preservePanels(),/revision_conflict/);conflict=false;await preservePanels();remove();
});
test('concurrent route transitions share one save promise',async()=>{
  let count=0;const remove=registerPreserver(async()=>{count++;await Promise.resolve();});
  const first=preservePanels(),second=preservePanels();assert.equal(first,second);await first;assert.equal(count,1);remove();
});
test('confirmed facts come from the authoritative dossier, not unrelated demo state',()=>{
  const project=projectOf({project:{id:'actual-uuid',name:'Dossier réel',reference:'REF',revision:8},facts:[{id:'accepted',field:'delivery_date',status:'accepted',kind:'date',value:'2027-01-04'},{id:'proposal',field:'delivery_date',status:'pending',value:'2027-02-01'},{id:'action',field:'action.1',status:'accepted',value:'Vérifier une pièce'}],pending:[{id:'proposal',field:'delivery_date',status:'pending',value:'2027-02-01'}]});
  assert.equal(project.id,'actual-uuid');assert.equal(project.revision,8);assert.equal(project.facts.length,2);assert.equal(project.pending.length,1);assert.equal(project.actions.length,1);assert.equal(project.actions[0].id,'action');assert.deepEqual(project.notes,[]);assert.deepEqual(project.sources,[]);
});
test('a dossier missing its revision is refused, never editable with a fabricated revision',()=>{
  assert.throws(()=>projectOf({id:'actual-uuid',name:'Incomplete'}),/incomplet/);
});
test('unavailable original stays unavailable and no file/version/amount is invented',()=>{
  const document=documentOf({source_id:'source',filename:'devis.pdf',available:false});
  assert.equal(document.id,null);assert.equal(document.available,false);assert.equal(document.size,null);assert.equal(document.preview_source_id,'');assert.equal('amount' in document,false);assert.equal('download_url' in document,false);
});
test('summary retains exact hashes, partial coverage, citations and stale state',()=>{
  const summary=summaryOf({id:'version-id',version:4,status:'draft',content:'Texte',content_hash:'content-hash',snapshot_hash:'snapshot-hash',snapshot_revision:9,stale:true,coverage:'partial',warnings:['Une pièce reste à vérifier.'],citations:[{source_id:'source',quote:'Passage exact.',start:4,end:18,source_hash:'proof-hash'}]});
  assert.equal(summary.snapshot_revision,9);assert.equal(summary.stale,true);assert.equal(summary.content_hash,'content-hash');assert.equal(summary.citations[0].quote,'Passage exact.');assert.equal(summary.citations[0].source_hash,'proof-hash');assert.equal(summary.coverage,'partial');
});
test('money stays a decimal string and comparison keeps the original source',()=>{
  const item=candidateOf({id:'proposal',kind:'money',field:'budget_raw',value:{amount:'1000000000000.01',currency:'EUR',basis:'HT'},source_id:'new-source',evidence:[{source_id:'new-source',quote:'Montant annoncé.'}],previous_values:[{id:'old',source_id:'original-source',value:{amount:'1200.00',currency:'EUR',basis:'HT'},evidence:[{source_id:'original-source',quote:'Montant initial.'}]}]});
  assert.equal(item.value.amount,'1000000000000.01');assert.equal(item.previous_values[0].source_id,'original-source');assert.equal(item.evidence[0].quote,'Montant annoncé.');
});
test('a native note revision can advance before decision, but unseen facts or proposals cannot',()=>{
  const before=projectOf({id:'project',revision:1,facts:[{id:'fact',field:'delivery_date',value:'2027-01-04',status:'accepted'}],pending:[{id:'proposal',field:'delivery_date',value:'2027-02-01',status:'pending'}]});
  const afterNotes={...before,revision:2,notes:[{id:'note',content:'Note humaine',actor_id:'actor',created_at:'',source_id:'source',origin:'manual_affine'}]};
  assert.equal(sameReviewContext(before,afterNotes),true);
  assert.equal(sameReviewContext(before,{...afterNotes,facts:[{...before.facts[0],value:'2027-03-01'}]}),false);
  assert.equal(sameReviewContext(before,{...afterNotes,pending:[]}),false);
});
