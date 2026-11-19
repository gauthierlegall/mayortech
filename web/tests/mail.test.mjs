import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeMail, normalizeMailList, renderMailMessage} from '../mail.js';

test('An HTML email is displayed as text and never becomes remote media or a script',()=>{
  const html=renderMailMessage({id:'mail-1',subject:'<script>alert("title")</script>',sender:'" onmouseover="alert(1)',body:'<img src="https://tracker.invalid/pixel" onerror="alert(1)"><a href="javascript:alert(2)">Cliquer</a>\n<script>alert(3)</script>'});
  assert(!/<img\s|<script\b|<a\s/i.test(html));
  assert(html.includes('&lt;img'));
  assert(html.includes('&lt;script&gt;'));
  assert(html.includes('&lt;a href='));
  assert(html.includes('https://tracker.invalid/pixel')); // retained as readable text, no request-capable element
});

test('Attachment attributes cannot escape their values',()=>{
  const html=renderMailMessage({metadata:{attachments:[{filename:'devis"><img src=x onerror=alert(1)>.pdf',source_id:'piece" onclick="alert(1)',status:'failed'}]}});
  assert(!/<img\s/i.test(html));
  assert(!/\s(?:onclick|onerror)="/i.test(html));
  assert(html.includes('Extraction en échec'));
  assert(!html.includes('Texte disponible'));
});

test('Unavailable and unknown extraction states never promise a readable attachment',()=>{
  const html=renderMailMessage({body:'Courrier',metadata:{attachments:[{filename:'plan.dwg',status:'new_unsupported_state'}]}});
  assert(html.includes('Texte non disponible'));
  assert(!html.includes('data-mail-source='));
  assert(html.includes('plan.dwg'));
});

test('Related extracted sources join the original attachment by filename',()=>{
  const mail=normalizeMail({id:'parent',body:'Texte',metadata:{attachments:[{filename:'devis.pdf',status:'extracted'}]},related_sources:[{source_id:'pdf-1',filename:'devis.pdf',kind:'pdf'}]});
  assert.equal(mail.attachments.length,1);
  assert.equal(mail.attachments[0].sourceId,'pdf-1');
  assert.equal(mail.attachments[0].filename,'devis.pdf');
});

test('A mail preserves all project references, recipients and the complete body',()=>{
  const body='Mémoire chantier\n'.repeat(400);
  const mail=normalizeMail({id:'1',project_ids:['a','b','a'],project_id:'b',sender:{name:'Entreprise test',address:'entreprise@example.invalid'},to:[{name:'Agent',email:'agent@example.invalid'},'service@example.invalid'],body});
  assert.deepEqual(mail.projectIds,['a','b']);
  assert.equal(mail.body,body);
  assert.equal(mail.sender,'Entreprise test <entreprise@example.invalid>');
  assert(mail.to.includes('service@example.invalid'));
  assert.equal(mail.preview.length,170);
});

test('List count is exact only when the API provides a valid total',()=>{
  assert.deepEqual(normalizeMailList({items:[{id:'1'}],total:17}).total,17);
  assert.equal(normalizeMailList({items:[{id:'1'}],total:-1}).totalKnown,false);
  assert.equal(normalizeMailList([{id:'1'}]).totalKnown,false);
  assert.equal(normalizeMailList({items:{}}).items.length,0);
});

test('Dates and recipient content remain safe even when malformed',()=>{
  const html=renderMailMessage({received_at:'<svg onload=alert(1)>',to:'<img src=x>',body:'Aucun HTML actif.'});
  assert(!html.includes('<svg onload='));
  assert(!html.includes('<img src='));
  assert(html.includes('&lt;img src=x&gt;'));
});

test('A new status with a project does not invent successful matching',()=>{
  const html=renderMailMessage({id:'x',project_id:'p',match_status:'uncertain_v2',body:'Texte'});
  assert(html.includes('Rattachement à vérifier'));
  assert(!html.includes('>Rattaché<'));
});
