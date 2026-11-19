import {useRef,useState,type FormEvent} from 'react';
import {ArrowRight,Landmark} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {useOrganizationModules} from './organization-modules-context';
import './work-profile.css';

const descriptions:Record<string,string>={
 'commission-1':'Dossiers, arbitrages financiers et échéances.',
 'commission-2':'Actions et dossiers enfance, jeunesse et action sociale.',
 'commission-3':'Urbanisme, suivi des travaux et carte du territoire.',
 'commission-4':'Agenda et dossiers culturels, sportifs et associatifs.',
};

const commissionModules:Record<string,string[]>={
 'commission-1':['finances_m57'],
 'commission-2':['enfance_ccas'],
 'commission-3':['urbanisme_ads','travaux_terrain'],
 'commission-4':['conseil_seances'],
};

export function WorkProfileChoice(){
 const {state,commissions,workProfile,setActiveCommissionId,refresh,api}=useWorkspace();
 const {hasModule}=useOrganizationModules();
 const visibleCommissions=commissions.filter(c=>{
  const req=commissionModules[c.id];
  if(!req)return true;
  return req.some(modKey=>hasModule(modKey));
 });
 const listToRender=visibleCommissions.length>0?visibleCommissions:commissions;
 const [selected,setSelected]=useState(''),[pending,setPending]=useState(false),[error,setError]=useState('');
 const inFlight=useRef(false);
 async function enter(event:FormEvent){
  event.preventDefault();if(inFlight.current||!selected)return;
  inFlight.current=true;setPending(true);setError('');
  try{await setActiveCommissionId(selected);window.location.hash='/';}
  catch(cause){setError(cause instanceof Error?cause.message:'Le profil n’a pas pu être ouvert. Actualisez vos accès.');}
  finally{inFlight.current=false;setPending(false);}
 }
 async function reload(){if(inFlight.current)return;inFlight.current=true;setPending(true);setError('');try{await refresh();}catch{setError('Les accès ne peuvent pas être actualisés. Réessayez.');}finally{inFlight.current=false;setPending(false);}}
 return <main id="main-content" className="content work-profile-choice" aria-busy={pending}>
  <a className="work-profile-brand" href="/espace.html"><Landmark size={20} aria-hidden="true"/>MayorTech<span>.</span></a>
  <p className="work-profile-organization">{state.organization||'Votre organisation'}</p>
  <h1>{workProfile.status==='unavailable'?'Vos accès aux commissions':'Choisir mon profil de travail'}</h1>
  {workProfile.status==='unavailable'?<>
   <p>Aucune commission ni aucun dossier ne vous est accessible pour le moment. Demandez à l’administrateur de votre organisation de vérifier vos accès.</p>
   <Button disabled={pending} onClick={()=>void reload()}>{pending?'Actualisation…':'Actualiser mes accès'}</Button>
  </>:<>
   <p>Choisissez la commission sur laquelle vous souhaitez travailler. Ses dossiers et ses vues métier seront affichés en priorité.</p>
   <form onSubmit={event=>void enter(event)}>
    <fieldset disabled={pending}><legend className="sr-only">Votre commission</legend>
     {listToRender.map(commission=><label key={commission.id} className={`work-profile-option ${selected===commission.id?'selected':''}`}>
      <input type="radio" name="work-profile" value={commission.id} checked={selected===commission.id} onChange={()=>setSelected(commission.id)}/>
      <span><strong>{commission.name}</strong><span>{descriptions[commission.id]||'Dossiers et suivi de la commission.'}</span></span>
      <small>{commission.can_edit===true?'Modification autorisée':'Lecture seule'}</small>
     </label>)}
    </fieldset>
    <Button type="submit" disabled={pending||!selected}>{pending?'Ouverture…':'Ouvrir mon espace'}<ArrowRight size={16}/></Button>
   </form>
   <p className="work-profile-help">Vous pouvez changer de profil depuis la navigation. Les profils proposés correspondent aux accès accordés par votre organisation.</p>
  </>}
  {error&&<p className="form-error" role="alert">{error}</p>}
  <Button className="work-profile-logout" variant="ghost" disabled={pending} onClick={()=>{if(inFlight.current)return;inFlight.current=true;setPending(true);void api.logout().then(()=>window.location.assign('/connexion.html')).catch(()=>{setError('La déconnexion n’a pas abouti. Réessayez.');inFlight.current=false;setPending(false);});}}>Se déconnecter</Button>
 </main>;
}
