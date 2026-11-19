import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeActionImports,partitionActionImports} from '../../../../native-editor/src/native-commands.mjs';
let model={};try{model=await import('./field-report-action.mjs');}catch{}
const report={id:'a67c5f44-b4da-4f89-a809-2a41e16b33b0',title:'Anomalie fictive',detail:'Texte fictif\n'.repeat(1600),author:'Équipe fictive',kind:'Anomalie'};

test('field report action keeps one stable source key and a bounded native description',()=>{
 const first=model.fieldReportAction?.(report,'2026-12-02');
 assert.ok(first);assert.equal(first.sourceKey,'field-report:'+report.id);
 assert.ok(first.description.length<=4000);assert.ok(first.description.includes(report.id));
 assert.equal(first.priority,'Haute');assert.equal(first.owner,report.author);
 assert.deepEqual(normalizeActionImports([first])[0],normalizeActionImports([model.fieldReportAction(report,'2026-12-02')])[0]);
});

test('retry reuses the real native import binding and never resurrects a deleted row',()=>{
 const input=model.fieldReportAction?.(report,'2026-12-02');assert.ok(input);
 const bindings=new Map([[input.sourceKey,{databaseId:'db',rowId:'row'}]]);
 const retry=partitionActionImports([input],bindings,id=>id==='row');
 assert.equal(retry.create.length,0);assert.equal(retry.existing[0].rowId,'row');
 const metadata={databases:[{id:'db',rows:[{id:'row',sourceKey:input.sourceKey}]}]};
 assert.deepEqual(model.fieldReportLink?.(input.sourceKey,retry,metadata,'page'),{page_id:'page',database_id:'db',row_id:'row'});
 const deleted=partitionActionImports([input],bindings,()=>false);
 assert.equal(deleted.create.length,0);
 assert.throws(()=>model.fieldReportLink(input.sourceKey,deleted,{databases:[]},'page'),/supprimée/);
});

test('a missing native metadata row cannot become a claimed action link',()=>{
 assert.throws(()=>model.fieldReportLink?.('field-report:'+report.id,{created:[],existing:[],deleted:[]},{databases:[]},'page'));
});
