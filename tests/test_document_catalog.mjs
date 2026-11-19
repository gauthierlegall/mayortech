import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveDocumentCatalog,verifiedDocumentReview} from '../frontend-lovable/src/features/workspace/document-catalog.ts';

const digest='a'.repeat(64);
function fixture(){
 const row={document_id:'doc1',source_id:'pdf1',mail_source_id:'mail1',filename:'devis-portail-v1.pdf',family:'AF-2026-184',version:1,status:'validated',status_label:'Validé',sha256:digest,amount:{amount:'4850.00',currency:'EUR',basis:'HT'},evidence:{version:{source_id:'pdf1',quote:'Devis AF-2026-184 - Version 1'},status:{source_id:'confirmation',quote:'Nous confirmons le devis initial de 4 850,00 € HT.'},amount:{source_id:'pdf1',quote:'Montant total : 4 850,00 EUR HT'}}};
 const source=(id,body,metadata={})=>({id,body,body_hash:'b'.repeat(64),metadata,project_ids:['project1']});
 const project={id:'project1',sources:[source('pdf1','Devis AF-2026-184 - Version 1\nMontant total : 4 850,00 EUR HT',{parent_source_id:'mail1',raw_sha256:digest}),source('mail1','Devis en pièce jointe'),source('confirmation','Nous confirmons le devis initial de 4 850,00 € HT.'),source('catalogue','Catalogue documentaire fictif préparé par l’opérateur.\n'+JSON.stringify([row]),{document_catalog:[row],note_id:'fixture-document-catalogue-v1',source_kind:'demo_document_catalog'})]};
 const document={id:'doc1',filename:'devis-fausse-version-99.pdf',kind:'attachment',source_id:'pdf1',parent_source_id:'mail1',sha256:digest,media_type:'application/pdf',available:true,warnings:[]};
 return {row,project,document};
}

test('business metadata comes from a catalogued original with exact proofs, never its filename',()=>{
 const {project,document}=fixture();const item=resolveDocumentCatalog(project,[document]).items[0];
 assert.equal(item.verified,true);assert.equal(item.version,1);assert.equal(item.amount.amount,'4850.00');assert.equal(item.statusLabel,'Validé');
});
test('a matching filename cannot bypass the original document hash or source association',()=>{
 const {project,document}=fixture();
 for(const altered of [{...document,sha256:'c'.repeat(64)},{...document,source_id:'foreign-pdf'},{...document,parent_source_id:'foreign-mail'}]){
  const item=resolveDocumentCatalog(project,[altered]).items[0];assert.equal(item.verified,false);assert.equal(item.version,null);assert.equal(item.amount,null);
 }
});
test('each quote must exist exactly in a source of this project',()=>{
 const {project,document}=fixture();project.sources.find(item=>item.id==='confirmation').body='Un autre texte';
 assert.equal(resolveDocumentCatalog(project,[document]).items[0].verified,false);
});
test('altering metadata without the catalog source body cannot manufacture a version',()=>{
 const {project,document,row}=fixture();row.version=2;
 assert.equal(resolveDocumentCatalog(project,[document]).items[0].verified,false);
});
test('two contradictory rows for the same original stay ambiguous',()=>{
 const {project,document,row}=fixture();const other={...row,version:2};const catalogue=project.sources.find(item=>item.id==='catalogue');
 catalogue.metadata.document_catalog.push(other);catalogue.body='Catalogue\n'+JSON.stringify(catalogue.metadata.document_catalog);
 assert.equal(resolveDocumentCatalog(project,[document]).items[0].verified,false);
});
test('a quote for 4850 does not establish a declaration of 5120',()=>{
 const {project,document,row}=fixture();row.amount.amount='5120.00';project.sources.find(item=>item.id==='catalogue').body='Catalogue\n'+JSON.stringify([row]);
 assert.equal(resolveDocumentCatalog(project,[document]).items[0].verified,false);
});
test('human document state must match its immutable original and precise note proof, including Unicode ranges',()=>{
 const {project,document}=fixture();const note={id:'human-note',body:'💡 Décision : document validé.',body_hash:'f'.repeat(64),project_ids:['project1'],metadata:{note_id:'note1'}};project.sources.push(note);
 const quote='document validé.',start=Array.from(note.body).indexOf('d');
 const row={document_id:'doc1',document_source_id:'pdf1',sha256:digest,status:'approved',status_label:'Validé',origin:'human_decision',source_id:note.id,can_review:true,evidence:{status:{source_id:note.id,source_hash:note.body_hash,start,end:start+Array.from(quote).length,quote}}};
 assert.equal(verifiedDocumentReview(row,project,document).status,'approved');
 assert.equal(verifiedDocumentReview({...row,sha256:'c'.repeat(64)},project,document),null);
 assert.equal(verifiedDocumentReview({...row,evidence:{status:{...row.evidence.status,source_hash:'b'.repeat(64)}}},project,document),null);
});
