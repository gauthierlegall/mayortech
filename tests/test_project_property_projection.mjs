import test from 'node:test';
import assert from 'node:assert/strict';
import {projectFromApi} from '../frontend-lovable/src/features/workspace/model.ts';
import {projectOf} from '../frontend-lovable/src/features/workspace/ProjectPanels.types.ts';
import {statusLabel} from '../web/model.js';

test('human property values including an explicit clear override the list projection without altering facts',()=>{
 const facts=[{id:'f',field:'location',value:'Lieu sourcé',status:'accepted'}];
 const properties={values:{location:'',service_owner:'Équipe fictive',category:'Bâtiments',contractor:'Entreprise fictive'},origins:{}};
 const projected=projectFromApi({id:'p',name:'Dossier fictif',status:'on_hold'},{facts,properties});
 assert.equal(projected.location,'');
 assert.equal(projected.owner,'Équipe fictive');
 assert.equal(projected.company,'Entreprise fictive');
 assert.equal(projected.category,'Bâtiments');
 assert.equal(projected.status,'En attente');
 assert.equal(statusLabel('on_hold'),'En attente');
 assert.equal(facts[0].value,'Lieu sourcé');
});

test('dossier properties survive typed parsing separately from confirmed facts',()=>{
 const result=projectOf({id:'p',revision:1,properties:{values:{estimated_cost:'15.20',deadline:'2026-12-01'},origins:{estimated_cost:{kind:'human_property'}}},facts:[]});
 assert.equal(result.properties.values.estimated_cost,'15.20');
 assert.equal(result.properties.origins.estimated_cost.kind,'human_property');
 assert.deepEqual(result.facts,[]);
});
