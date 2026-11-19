import {describe,it,expect} from 'vitest';
import {makeSeed,receiveMail,confirmDelivery} from './model';
describe('Scénario du portail',()=>{
 it('contient cinq mails et une livraison initiale au 18 novembre',()=>{const s=makeSeed();expect(s.messages.filter(m=>m.projectId==='portail')).toHaveLength(5);expect(s.projects[0]?.delivery).toBe('2026-11-18');});
 it('rattache le nouveau mail sans doublon et crée une seule action accès',()=>{const s=receiveMail(receiveMail(makeSeed()));expect(s.projects).toHaveLength(4);expect(s.messages.filter(m=>m.id==='m6')).toHaveLength(1);expect(s.actions.filter(a=>a.title==='Confirmer l’accès vendredi')).toHaveLength(1);});
 it('ne confirme pas automatiquement le report annoncé',()=>{expect(receiveMail(makeSeed()).projects[0]?.delivery).toBe('2026-11-18');});
 it('confirme le 25 novembre et conserve ancienne valeur et source',()=>{const s=confirmDelivery(receiveMail(makeSeed()));expect(s.projects[0]?.delivery).toBe('2026-11-25');expect(s.history.at(-1)).toMatchObject({detail:'2026-11-18 → 2026-11-25',source:'m6',author:'Thomas Le Gall'});});
 it('ne remplace pas le devis validé par le dernier devis reçu',()=>{const s=receiveMail(makeSeed());expect(s.documents[0]?.status).toBe('Validé');expect(s.documents[1]?.status).toBe('En examen');});
 it('préserve les notes humaines après une confirmation',()=>{const s=receiveMail(makeSeed());s.notes['portail']='Note personnelle';expect(confirmDelivery(s).notes['portail']).toBe('Note personnelle');});
});
