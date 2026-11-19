const generic={title:'Dossiers',views:['projects'],defaultView:'projects',properties:'Demande, suivi, budget et observations du service.',propertyOrder:[]};
const profiles={
  'commission-1':{title:'Commission Finances',views:['arbitration','projects','sessions'],defaultView:'arbitration',properties:'Coûts estimés et réels, dates de suivi et responsable.',propertyOrder:['name','status','estimated_cost','actual_cost','priority','deadline','service_owner']},
  'commission-2':{title:'Commission Enfance, Jeunesse & Solidarités',views:['campaigns','projects','actions','sessions'],defaultView:'campaigns',properties:'Responsables, échéances et demandes.',propertyOrder:['name','status','priority','service_owner','deadline','requester','request_date']},
  'commission-3':{title:'Commission Urbanisme, Travaux & Ports',views:['projects','map','sessions'],defaultView:'projects',properties:'Lieu, entreprise et échéances du dossier.',propertyOrder:['name','status','location','contractor','deadline','service_owner','priority']},
  'commission-4':{title:'Commission Culture',views:['agenda','projects','sessions'],defaultView:'agenda',properties:'Dates, lieu et responsable de la coordination.',propertyOrder:['name','status','deadline','location','service_owner','requester','category']},
};

/** Presentation only: the workspace supplies the server-authorized commission. */
export function presentationForCommission(commissionId){return profiles[commissionId]||generic;}
export function projectViewForCommission(commissionId,requested){
  const profile=presentationForCommission(commissionId);
  return profile.views.includes(requested)?requested:profile.defaultView;
}
/** @template {{key:string}} T @param {T[]} fields @param {string} commissionId @returns {T[]} */
export function orderPropertyFields(fields,commissionId){
  const order=presentationForCommission(commissionId).propertyOrder;
  const rank=key=>{const index=order.indexOf(key);return index<0?order.length:index;};
  return [...fields].sort((a,b)=>rank(a.key)-rank(b.key));
}
