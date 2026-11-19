export function canLogoutWorkspace(session){
 return session?.authenticated===true&&session?.auth_required===true&&session?.public_demo!==true;
}

/** The server confirms revocation before the UI drops its account scope. */
export async function logoutWorkspace({session,api,preserve,assertCurrent,onRevoked,redirect}){
 if(!canLogoutWorkspace(session))throw Error('La déconnexion n’est pas disponible dans cet espace.');
 assertCurrent();
 try{await preserve();}
 catch{throw Error('Vos modifications n’ont pas pu être enregistrées. Enregistrez-les avant de vous déconnecter.');}
 assertCurrent();
 let response;
 try{response=await api.logout();}
 catch{assertCurrent();throw Error('La déconnexion n’a pas abouti. Réessayez.');}
 assertCurrent();
 if(!response||typeof response!=='object'||response.authenticated!==false)throw Error('La déconnexion n’a pas pu être confirmée. Réessayez.');
 onRevoked();
 redirect();
}
