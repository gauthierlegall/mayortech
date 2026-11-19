import assert from 'node:assert/strict';
import test from 'node:test';
import {importedWorkbook,mentionedDates} from './project-import-model.mjs';

const source = {origin:'local_workbook_import',content:JSON.stringify({
 schema:'mayortech.local-workbook-import/v1',row_number:4,
 notion_reference:{url:'https://notion.so/0123456789abcdef0123456789abcdef'},
 source_cells:[{header:'Échéance',type:'datetime',value:'2026-11-30T14:25:00'},{header:'Demandeur',type:'text',value:'Personne fictive'}],
 unmapped_values:[{field:'priority',value:'À revoir',reason:'outside_allowed_values'}],
})};

test('shows only the preserved exact import values that need a separate display',()=>{
 const result=importedWorkbook([source]);
 assert.equal(result.row,4);
 assert.deepEqual(result.originalTimes,[{label:'Échéance',day:'2026-11-30',time:'14:25:00'}]);
 assert.deepEqual(result.unmapped,[{label:'Priorité',value:'À revoir'}]);
 assert.equal(result.notionUrl,'https://notion.so/0123456789abcdef0123456789abcdef');
});

test('requires an import note and validates the outbound URL',()=>{
 assert.equal(importedWorkbook([{...source,origin:'manual'}]),null);
 const value=JSON.parse(source.content);value.notion_reference.url='https://notion.so.attacker.invalid/0123456789abcdef0123456789abcdef';
 assert.equal(importedWorkbook([{...source,content:JSON.stringify(value)}]).notionUrl,'');
});

test('mentions deduplicate real civil dates and exclude typed dates and impossible dates',()=>{
 assert.deepEqual(mentionedDates({request_date:'2026-11-02',deadline:'2026-11-03',notes:'02/11/2026, 2026-11-16, 31/11/2026, 16/11/2026',observation:'24/11/2026 et le 03/11/2026'}),['2026-11-16','2026-11-24']);
});
