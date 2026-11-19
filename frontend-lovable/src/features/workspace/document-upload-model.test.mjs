import test from 'node:test';
import assert from 'node:assert/strict';
import {documentUploadAccess,validateUploadFile,prepareDocumentUpload,uploadReceipt} from './document-upload-model.mjs';

test('upload requires server write permission and excludes only public demonstration',()=>{
 assert.equal(documentUploadAccess({public_demo:true},{permissions:{workspace:{write:true}}}),false);
 assert.equal(documentUploadAccess({public_demo:false,demo:true},{permissions:{workspace:{write:true}}}),true);
 assert.equal(documentUploadAccess({},{}),false);
 assert.equal(documentUploadAccess({},{permissions:{workspace:{write:false}}}),false);
});
test('file validation matches the server size, names and extension boundary',()=>{
 assert.equal(validateUploadFile({name:'Plan de voirie.PDF',size:5_000_000}), '');
 for(const file of [{name:'plan.pdf',size:5_000_001},{name:'plan.pdf',size:0},{name:'plan.exe',size:1},{name:'../plan.pdf',size:1},{name:'C:plan.pdf',size:1},{name:'a\n.pdf',size:1},{name:'x'.repeat(181)+'.txt',size:1}]) assert.ok(validateUploadFile(file));
 for(const name of ['note.docx','note.txt','note.md','note.csv'])assert.equal(validateUploadFile({name,size:1}),'');
});
test('preparation preserves exact bytes and a caller-owned retry identifier',async()=>{
 const bytes=Uint8Array.of(0,128,255,10,195,169);
 const result=await prepareDocumentUpload({name:'note.txt',size:bytes.length,arrayBuffer:async()=>bytes.buffer},'upload-1');
 assert.deepEqual(result,{filename:'note.txt',content_base64:'AID/CsOp',client_id:'upload-1'});
});
test('invalid or changed files never reach the upload payload',async()=>{
 await assert.rejects(()=>prepareDocumentUpload({name:'mail.eml',size:2,arrayBuffer:async()=>new ArrayBuffer(2)},'id'));
 await assert.rejects(()=>prepareDocumentUpload({name:'note.txt',size:2,arrayBuffer:async()=>new ArrayBuffer(3)},'id'));
});
test('receipt must match the selected dossier and reports failed analysis honestly',()=>{
 const raw={status:'needs_review',project_id:'p1',source_id:'s1',document_id:'d1',job_id:'j1',job_status:'failed',extraction_status:'extracted',candidate_count:0,document:{id:'d1'},warnings:['Analyse indisponible'],replayed:false};
 const receipt=uploadReceipt(raw,'p1');
 assert.equal(receipt.document_id,'d1');assert.match(receipt.message,/analyse.*abouti/i);
 assert.throws(()=>uploadReceipt(raw,'p2'));
 assert.throws(()=>uploadReceipt({...raw,document:{id:'d2'}},'p1'));
});
test('receipt distinguishes queued analysis, extracted candidates and empty text',()=>{
 const raw={status:'needs_review',project_id:'p',source_id:'s',document_id:'d',job_id:'j',job_status:'done',extraction_status:'extracted',candidate_count:2,document:{id:'d'},warnings:[]};
 assert.match(uploadReceipt(raw,'p').message,/2 propositions.*relire/);
 assert.match(uploadReceipt({...raw,job_status:'queued'},'p').message,/attente/);
 assert.match(uploadReceipt({...raw,extraction_status:'failed',candidate_count:0},'p').message,/texte exploitable/);
 assert.match(uploadReceipt({...raw,job_status:'unavailable',candidate_count:0},'p').message,/état de l’analyse.*indisponible/);
});
