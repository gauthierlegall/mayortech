import {escapeHtml as e,dateLabel,listOf} from './model.js';
import {palettes,getAppearance,setAppearance} from './appearance.js';

const sections=[['appearance','Apparence'],['organization','Organisation'],['members','Membres'],['roles','Rôles et droits'],['audit','Journal'],['connections','Connexions']];
const labels={organization:'Organisation',members:'Membres',roles:'Rôles',audit:'Journal',workspace:'Chantiers',mail:'Messagerie',mail_flags:'Classement des courriels',read:'Consulter',write:'Modifier',flags:'Classer les messages'};
const eventLabels={'organization.updated':'Organisation modifiée','project.created':'Chantier créé','source.ingested':'Courriel ajouté','source.assigned':'Courriel rattaché','candidate.accepted':'Information confirmée','candidate.rejected':'Proposition écartée','candidate.corrected':'Information corrigée','candidate.replaced':'Information remplacée','note.added':'Note ajoutée','summary.created':'Récapitulatif préparé','summary.approved':'Récapitulatif validé','native_page.saved':'Notes enregistrées','page.saved':'Notes enregistrées','workspace.note_imported':'Notes du document enregistrées','document.stored':'Document conservé'};
export function settingsMarkup(section='appearance'){
  if(!sections.some(([id])=>id===section))section='appearance';
  return `<div class="settings-layout"><nav class="settings-nav" aria-label="Paramètres">${sections.map(([id,label])=>`${id==='organization'?'<span class="settings-nav-label">Administration de l’espace</span>':''}<a href="#/settings/${id}"${id===section?' class="selected" aria-current="page"':''}>${label}</a>`).join('')}</nav><section class="settings-content" id="settings-content" aria-live="polite"></section></div>`;
}

export async function mountSettings(container,{api,section='appearance',onSaved}={}){
  let disposed=false;
  const fail=error=>{if(!disposed)container.innerHTML=`<p class="notice danger" role="alert">${e(error.message||'Les paramètres sont indisponibles. Rechargez cette page.')}</p>`;};
  function appearance(){
    const value=getAppearance();
    container.innerHTML=`<h2>Apparence</h2><fieldset class="settings-fieldset"><legend>Couleur de l’espace</legend><div class="palette-options">${palettes.map(p=>`<label class="palette-option" style="--sample-accent:${p.accent};--sample-soft:${p.soft}"><input type="radio" name="color" value="${p.id}"${p.id===value.color?' checked':''}><span class="palette-preview" aria-hidden="true"><span class="palette-rail"></span><span class="palette-lines"><i></i><i></i><i></i></span></span><span>${p.name}</span></label>`).join('')}</div></fieldset><fieldset class="settings-fieldset"><legend>Espacement</legend><div class="density-options"><label><input type="radio" name="density" value="compact"${value.density==='compact'?' checked':''}>Compact</label><label><input type="radio" name="density" value="comfortable"${value.density==='comfortable'?' checked':''}>Confortable</label></div></fieldset><p class="settings-note" role="status">Les changements s’appliquent immédiatement sur cet appareil.</p>`;
  }
  const change=event=>{if(['color','density'].includes(event.target.name)){setAppearance({[event.target.name]:event.target.value});onSaved?.();}};
  container.addEventListener('change',change);
  try{
    if(section==='appearance')appearance();
    else if(section==='organization'){
      const org=await api.organization();if(disposed)return;
      container.innerHTML=`<h2>Organisation</h2><form data-settings-form="organization"><div class="form-field"><label for="organization-name">Nom de l’organisation</label><input class="input" id="organization-name" name="name" value="${e(org.name||'')}" required maxlength="200"${org.can_manage?'':' readonly'}></div><div class="form-field"><label for="organization-service">Service</label><input class="input" id="organization-service" name="service" value="${e(org.service||'')}" maxlength="200"${org.can_manage?'':' readonly'}></div><input type="hidden" name="expected_revision" value="${e(org.revision??0)}">${org.can_manage?'<button class="btn primary" type="submit">Enregistrer</button>':'<p class="settings-note">Ces informations sont gérées par l’administrateur de l’espace.</p>'}<p class="settings-feedback" role="status"></p></form>`;
    }else if(section==='members'){
      const data=await api.organizationMembers();if(disposed)return;
      const members=listOf(data.items||data.members||data);
      container.innerHTML=`<h2>Membres</h2><div class="members-list">${members.map(member=>`<article class="member-row"><span class="member-avatar" aria-hidden="true">${e((member.name||member.display_name||'V').slice(0,1))}</span><div><strong>${e(member.name||member.display_name||'Membre de l’espace')}</strong>${member.email?`<p>${e(member.email)}</p>`:''}</div><span>${e(member.role_label||member.role_name||({admin:'Administrateur',editor:'Éditeur',reader:'Lecteur',visitor:'Visiteur'}[member.role])||member.role||'Visiteur')}</span></article>`).join('')}</div>${data.capabilities?.identity_provider===false||data.identity_provider===false?'<p class="settings-note">L’espace utilise actuellement un accès partagé. Les invitations nécessitent un fournisseur d’identité connecté.</p>':''}`;
    }else if(section==='roles'){
      const data=await api.organizationRoles();if(disposed)return;
      const roles=listOf(data.items||data.roles||data);
      const permissions=[...new Map(roles.flatMap(role=>listOf(role.permissions).map(grant=>[grant.resource+':'+grant.action,grant]))).values()];
      container.innerHTML=`<h2>Rôles et droits</h2><p class="settings-intro">Les droits associés à chaque rôle dans cet espace.</p><div class="permissions-table" role="region" aria-label="Droits des rôles, tableau défilant" tabindex="0"><table><thead><tr><th>Droit</th>${roles.map(role=>`<th scope="col">${e(role.name||role.id)}</th>`).join('')}</tr></thead><tbody>${permissions.map(grant=>`<tr><th scope="row">${e(labels[grant.resource]||grant.resource)}<span>${e(labels[grant.action]||grant.action)}</span></th>${roles.map(role=>{const allowed=listOf(role.permissions).some(item=>item.resource===grant.resource&&item.action===grant.action&&item.allowed);return `<td><span class="permission-${allowed?'yes':'no'}" aria-label="${allowed?'Autorisé':'Non autorisé'}">${allowed?'✓':'—'}</span></td>`;}).join('')}</tr>`).join('')}</tbody></table></div>${data.capabilities?.identity_provider===false?'<p class="settings-note">Les comptes individuels et les invitations seront disponibles après connexion d’un fournisseur d’identité.</p>':''}`;

    }else if(section==='audit'){
      const data=await api.organizationAudit();if(disposed)return;
      const entries=listOf(data.items||data.events||data);
      container.innerHTML=`<h2>Journal de l’espace</h2>${entries.length?`<ol class="organization-journal">${entries.map(entry=>`<li><time>${e(dateLabel(entry.created_at||entry.date||entry.timestamp,true))}</time><div><strong>${e(entry.label||entry.action_label||eventLabels[entry.action]||entry.action||entry.type||'Modification')}</strong>${entry.project_name?`<p>${e(entry.project_name)}</p>`:''}${(entry.actor_name||entry.actor_label)?`<small>${e(entry.actor_name||entry.actor_label)}</small>`:''}</div></li>`).join('')}</ol>`:'<p class="settings-note">Les décisions et modifications de cet espace apparaîtront ici.</p>'}`;
    }else{
      const data=await api.settings();if(disposed)return;
      const caps=data.capabilities||{};
      container.innerHTML=`<h2>Connexions</h2><div class="connection-rows">${[['exchange','Messagerie'],['llm','Analyse des courriels']].map(([key,label])=>`<div><strong>${label}</strong><span>${['ready','connected'].includes(caps[key]?.status)?'Connectée':'Non connectée'}</span></div>`).join('')}</div><p class="settings-note">La messagerie institutionnelle se raccorde avec les paramètres fournis par son administrateur.</p>`;
    }
  }catch(error){fail(error);}
  const submit=async event=>{
    if(event.target.dataset.settingsForm!=='organization')return;event.preventDefault();
    const form=event.target,data=new FormData(form),feedback=form.querySelector('.settings-feedback'),button=form.querySelector('button');
    button.disabled=true;try{const saved=await api.saveOrganization({name:String(data.get('name')).trim(),service:String(data.get('service')).trim(),expected_revision:Number(data.get('expected_revision'))});form.elements.expected_revision.value=saved.revision;feedback.textContent='Enregistré.';}catch(error){feedback.textContent=error.message;}finally{button.disabled=false;}
  };
  container.addEventListener('submit',submit);
  return{destroy(){disposed=true;container.removeEventListener('change',change);container.removeEventListener('submit',submit);}};
}
