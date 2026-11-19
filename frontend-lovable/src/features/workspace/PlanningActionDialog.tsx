import {useEffect,useId,useState} from 'react';
import {MessageSquare} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogDescription,DialogTitle} from '@/components/ui/dialog';
import {statuses as managedStatuses} from './model';
import {planningActionGroups,planningConsistencyWarning,planningFormDirty,planningOwnerChoices,validDay} from './planning-model.mjs';
import type {NativeAction} from './native-actions';

interface Props {open:boolean;projectId?:string;items:NativeAction[];projects:{id:string;title:string}[];selected:NativeAction|null;canWrite:boolean;busy:boolean;start:string;end:string;progress:string;owner:string;status:string;owners:string[];error:string;onSelect:(action:NativeAction)=>void;onClearSelection:()=>void;onStart:(value:string)=>void;onEnd:(value:string)=>void;onProgress:(value:string)=>void;onOwner:(value:string)=>void;onStatus:(value:string)=>void;onSave:()=>Promise<void>;onClose:()=>void;onSource?:(sourceId:string)=>void}
type PendingChoice={kind:'action';action:NativeAction}|{kind:'project';projectId:string};

/** One form for the existing action; choosing or removing dates never saves implicitly. */
export function PlanningActionDialog({open,projectId,items,projects,selected,canWrite,busy,start,end,progress,owner,status,owners,error,onSelect,onClearSelection,onStart,onEnd,onProgress,onOwner,onStatus,onSave,onClose,onSource}:Props){
 const ownerListId=useId(),[chosenProject,setChosenProject]=useState(projectId||''),[pendingChoice,setPendingChoice]=useState<PendingChoice|null>(null);
 useEffect(()=>{if(open&&!selected)setChosenProject(projectId||'');setPendingChoice(null);},[open,projectId]);
 useEffect(()=>{if(selected)setChosenProject(selected.projectId);setPendingChoice(null);},[selected?.projectId,selected?.id]);
 const groups=planningActionGroups(items,projects),ownerChoices=planningOwnerChoices(owners,items,selected?.projectId===chosenProject?selected.owner:'',chosenProject);
 const statusChoices=[...new Set([...managedStatuses,...(selected?.status?[selected.status]:[''])])];
 const dirty=planningFormDirty(selected,start,end,progress,owner,status),warning=planningConsistencyWarning(status,progress);
 const projectName=projects.find(project=>project.id===projectId)?.title||'Chantier ouvert';
 const projectActions=groups.find(group=>group.id===chosenProject)?.items||[];
 function choose(value:string){
  const action=projectActions.find(item=>`${item.projectId}:${item.id}`===value);if(!action||action.id===selected?.id&&action.projectId===selected.projectId)return;
  if(dirty)setPendingChoice({kind:'action',action});else onSelect(action);
 }
 function changeProject(value:string){if(value===chosenProject)return;if(dirty)setPendingChoice({kind:'project',projectId:value});else{setChosenProject(value);onClearSelection();}}
 function confirmChoice(){if(!pendingChoice)return;if(pendingChoice.kind==='action')onSelect(pendingChoice.action);else{setChosenProject(pendingChoice.projectId);onClearSelection();}setPendingChoice(null);}
 return <Dialog open={open} onOpenChange={value=>{if(!value&&!busy)onClose();}}><DialogContent className="planning-edit-dialog max-h-[90dvh] overflow-y-auto">
  <DialogTitle>{canWrite?'Planifier une action':'Consulter une action'}</DialogTitle>
  <DialogDescription>{selected?'Les modifications seront partagées avec le suivi Actions. Les dates confirmées du chantier et les rendez-vous restent inchangés.':projectId?'Choisissez une action existante pour renseigner ses dates et son suivi.':'Choisissez un chantier, puis l’action à planifier.'}</DialogDescription>
  <form className="form-stack" onSubmit={event=>{event.preventDefault();if(selected&&selected.projectId===chosenProject&&!pendingChoice)void onSave();}}>
   {projectId?<p className="planning-action-project"><span>Chantier</span><strong>{projectName}</strong></p>:<label>Chantier<select aria-label="Chantier de l’action" value={chosenProject} disabled={busy||Boolean(pendingChoice)} required onChange={event=>changeProject(event.target.value)}><option value="" disabled>Choisir un chantier…</option>{projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select></label>}
   <label>Action existante<select aria-label="Action à planifier" value={selected?`${selected.projectId}:${selected.id}`:''} disabled={!chosenProject||busy||Boolean(pendingChoice)} required onChange={event=>choose(event.target.value)}><option value="" disabled>{chosenProject?'Choisir une action…':'Choisissez d’abord un chantier'}</option>{projectActions.map(action=><option key={`${action.projectId}:${action.id}`} value={`${action.projectId}:${action.id}`}>{action.title}</option>)}</select></label>
   {!selected&&<p className="planning-form-help">{chosenProject&&!projectActions.length?'Ce chantier n’a pas encore d’action. ':''}L’action n’existe pas encore ? <a href={chosenProject?`#/chantiers/${encodeURIComponent(chosenProject)}?view=table`:'#/actions'} onClick={onClose}>{chosenProject?'Créer une action dans ce chantier':'Créer une action dans le suivi'}</a>.</p>}
   {pendingChoice&&<div className="planning-switch-confirm" role="alert"><p>Changer {pendingChoice.kind==='project'?'de chantier':'d’action'} effacera la saisie non enregistrée de ce formulaire.</p><div><Button type="button" variant="outline" onClick={()=>setPendingChoice(null)}>Conserver ma saisie</Button><Button type="button" onClick={confirmChoice}>Choisir l’autre {pendingChoice.kind==='project'?'chantier':'action'}</Button></div></div>}
   {selected&&<>
    <fieldset className="planning-edit-fields" disabled={!canWrite||busy||Boolean(pendingChoice)}>
     <div className="planning-date-fields"><label><span>Début <span className="planning-optional">(facultatif)</span></span><input type="date" value={start} max={end||undefined} onChange={event=>onStart(event.target.value)}/></label><label><span>Échéance <span className="planning-optional">(facultative)</span></span><input type="date" value={end} min={start||undefined} onChange={event=>onEnd(event.target.value)}/></label></div>
     <p className="planning-form-help">Un début et une échéance affichent l’action dans la frise. Un champ vide reste non renseigné.</p>
     {validDay(selected.start)&&!start&&<p className="planning-form-help" role="status">La date de début sera effacée à l’enregistrement. L’échéance et les autres champs sont conservés tels que saisis.</p>}
      <label>Responsable<input list={ownerListId} value={owner} placeholder="Nom ou service — facultatif" maxLength={200} onChange={event=>onOwner(event.target.value)}/><datalist id={ownerListId}>{ownerChoices.map(value=><option key={value} value={value}/>)}</datalist><small>Suggestions issues des actions de ce chantier. Vous pouvez saisir un autre nom ou service.</small></label>
     <label>Statut<select value={status} onChange={event=>onStatus(event.target.value)}>{statusChoices.map(value=><option key={value} value={value}>{value||'Non renseigné'}</option>)}</select></label>
     <label>Avancement (%)<input type="number" min="0" max="100" step="1" value={progress} placeholder="Non renseigné" onChange={event=>onProgress(event.target.value)}/><small>Facultatif. Le statut ne modifie pas automatiquement ce pourcentage.</small></label>
     {warning&&<p className="planning-form-warning" role="status">{warning}</p>}
    </fieldset>
    {selected.source&&<Button variant="link" type="button" disabled={busy||Boolean(pendingChoice)} onClick={()=>{if(onSource)onSource(selected.source!);else{onClose();location.hash=`#/mail/${encodeURIComponent(selected.source!)}`;}}}><MessageSquare size={15}/>Voir le message lié</Button>}
    {error&&<p className="form-error" role="alert">{error}</p>}
   </>}
   <div className="planning-form-footer"><Button type="button" variant="outline" disabled={busy} onClick={onClose}>{canWrite?'Annuler':'Fermer'}</Button>{selected&&canWrite&&<Button type="submit" disabled={busy||Boolean(pendingChoice)}>{busy?'Enregistrement…':'Enregistrer les modifications'}</Button>}</div>
   {selected&&canWrite&&validDay(start)&&<Button type="button" className="planning-remove-dates" variant="ghost" disabled={busy||Boolean(pendingChoice)} onClick={()=>onStart('')}>Retirer de la frise</Button>}
  </form>
 </DialogContent></Dialog>;
}
