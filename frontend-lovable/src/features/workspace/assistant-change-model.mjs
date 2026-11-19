const labels={name:'Dossier',category:'Catégorie',status:'Statut',priority:'Priorité',request_date:'Date de demande',deadline:'Échéance',requester:'Demandeur',service_owner:'Service / Responsable',contractor:'Entreprise',location:'Lieu',estimated_cost:'Coût estimé',actual_cost:'Coût réel',notes:'Notes',observation:'Observation'};
export function canRequestChange(bootstrap,projectId){return Boolean(projectId&&bootstrap?.permissions?.workspace?.write===true);}
export function messageAttempt(previous,{threadId,content,intent},newId){
 content=typeof content==='string'?content.trim():'';
 if(!threadId||!content||!['question','change'].includes(intent))throw Error('Choisissez une question ou une modification et saisissez votre demande.');
 if(previous?.threadId===threadId&&previous?.content===content&&previous?.intent===intent)return previous;
 return {threadId,content,intent,clientId:newId()};
}
export function assistantProposal(raw,{id,conversationId,projectId}){
 const plan=raw?.plan;
 if(!id||!projectId||!conversationId||raw?.id!==id||raw?.project_id!==projectId||raw?.conversation_id!==conversationId||!['pending','applied','rejected'].includes(raw.status)||!Number.isFinite(raw.expires_at)||!/^[a-f0-9]{64}$/.test(raw.plan_hash)||!plan||!['property','note','action'].includes(plan.operation)||typeof plan.value!=='string'||!plan.value.trim()||plan.value.length>4000||(plan.operation==='property'&&!Object.hasOwn(labels,plan.field))||(plan.operation!=='property'&&plan.field!==''))throw Error('Cette proposition ne correspond pas à la conversation et au dossier. Aucun changement n’est possible ; actualisez la proposition.');
 return {id:raw.id,project_id:raw.project_id,conversation_id:raw.conversation_id,plan:{operation:plan.operation,field:plan.field,value:plan.value},plan_hash:raw.plan_hash,status:raw.status,result:raw.result||{},expires_at:raw.expires_at};
}
export function proposalPresentation(proposal){return {label:proposal.plan.operation==='property'?labels[proposal.plan.field]:proposal.plan.operation==='action'?'Créer une action':'Ajouter une note',value:proposal.plan.value};}
