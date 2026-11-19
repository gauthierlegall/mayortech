import test from 'node:test';
import assert from 'node:assert/strict';
let model = {};
try { model = await import('../model.js'); } catch {}

test('email text is rendered as text even when it contains executable HTML', () => {
  assert.equal(model.escapeHtml?.('<img src=x onerror="alert(1)">&'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&amp;');
});
test('external links reject executable and protocol-relative URLs', () => {
  assert.equal(model.safeUrl?.('javascript:alert(1)'), '');
  assert.equal(model.safeUrl?.('//example.org'), '');
  assert.equal(model.safeUrl?.('https://mairie.test/workspace'), 'https://mairie.test/workspace');
});
test('approval requires current content, snapshot and project revision', () => {
  assert.equal(model.canApprove?.({status:'draft',content:'Texte',content_hash:'a',snapshot_hash:'b',project_revision:0}), true);
  assert.equal(model.canApprove?.({status:'draft',content:'Texte',content_hash:'a',project_revision:1}), false);
  assert.equal(model.canApprove?.({status:'stale',content:'Texte',content_hash:'a',snapshot_hash:'b',project_revision:1}), false);
});
test('new unreviewed source coverage prevents approval even when the content hash is intact', () => {
  assert.equal(model.canApprove?.({status:'draft',content:'Texte',content_hash:'a',snapshot_hash:'b',project_revision:2,coverage_stale:true}), false);
});
test('unknown statuses remain visible rather than being described as validated', () => {
  assert.equal(model.statusLabel?.('unexpected_backend_state'), 'unexpected_backend_state');
  assert.equal(model.statusLabel?.('proposed'), 'À vérifier');
});
test('empty and absent values remain distinct from zero', () => {
  assert.equal(model.displayValue?.(0), '0');
  assert.equal(model.displayValue?.(null), 'Non renseigné');
  assert.equal(model.displayValue?.({amount:'12000.00',currency:'EUR',tax_basis:'HT'}), '12000.00 EUR HT');
});

test('completed and legacy closed projects share the Terminé filter without hiding either', () => {
  const projects=[{id:'done',name:'Éclairage',status:'completed'},{id:'legacy',name:'Salle',status:'closed'},{id:'active',status:'active'}];
  assert.deepEqual(model.filterProjects?.(projects,{status:'completed'}).map(p=>p.id),['done','legacy']);
  assert.deepEqual(model.filterProjects?.(projects,{status:'closed'}).map(p=>p.id),['done','legacy']);
  assert.equal(model.statusLabel?.('closed'),'Terminé');
});

test('project search keeps exact references and prioritizes work awaiting a human decision', () => {
  const projects=[{id:'old',reference:'TRV-003',name:'Port',status:'completed',updated_at:'2026-11-14'},
    {id:'review',reference:'TRV-014',name:'École',status:'active',pending_count:3,updated_at:'2026-11-12'},
    {id:'active',reference:'TRV-021',name:'Rue',status:'active',updated_at:'2026-11-13'}];
  const order=projects.map(p=>p.id);
  assert.deepEqual(model.prioritizeProjects?.(projects).map(p=>p.id),['review','old','active']);
  assert.deepEqual(projects.map(p=>p.id),order);
  assert.deepEqual(model.filterProjects?.(projects,{term:' trv-014 ',status:'active'}).map(p=>p.id),['review']);
  assert.deepEqual(model.filterProjects?.(projects,{term:'inexistant'}),[]);
});
