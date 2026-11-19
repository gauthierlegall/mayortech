import {Link,useLocation} from '@tanstack/react-router';
import {Mail,HardHat,CheckCheck,Settings,Star,PanelLeftClose,PanelLeftOpen,Landmark,Menu,X,ShieldCheck,ChevronDown,FlaskConical,CalendarDays,ChartNoAxesGantt,ClipboardCheck,GitBranch,Plus,UserCheck,CheckCircle2,Sun,Search,Sparkles,FileText,Coins,Users,Heart,Building2,MapPin,Map} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {useEffect,useRef,useState,type ReactNode,type CSSProperties} from 'react';
import {getAppearance,palettes} from '../../../../web/appearance.js';
import {applyWorkspaceAppearance} from './appearance-adapter';
import {AssistantWidget} from './AssistantWidget';
import {mailFolderUnread,workspaceMailIdentity} from './mail-navigation-state.mjs';
import {WorkspaceLogout} from './WorkspaceLogout';
import {useOrganizationModules} from './organization-modules-context';
import {OrganizationCreationWizardModal} from './OrganizationCreationWizardModal';
import {AbsenceDelegationModal} from './AbsenceDelegationModal';
import {CommandPaletteModal} from './CommandPaletteModal';
import {getCommissionConfig} from './commissionConfig';

const commissionModules:Record<string,string[]>={
 'commission-1':['finances_m57'],
 'commission-2':['enfance_ccas'],
 'commission-3':['urbanisme_ads','travaux_terrain'],
 'commission-4':['conseil_seances'],
};

export function Shell({children}:{children:ReactNode}){
 const {state,session,bootstrap,activeCommissionId,setActiveCommissionId,activeCommission,commissions,workProfileNotice}=useWorkspace();
 const {hasModule,organization,isWizardOpen,setIsWizardOpen}=useOrganizationModules();
 const commissionCfg=getCommissionConfig(activeCommissionId);
 const visibleCommissions=commissions.filter(c=>{
  const req=commissionModules[c.id];
  if(!req)return true;
  return req.some(modKey=>hasModule(modKey));
 });
 const [isOrgMenuOpen,setIsOrgMenuOpen]=useState(false);
 const [isDelegationOpen,setIsDelegationOpen]=useState(false);
 const [isPaletteOpen,setIsPaletteOpen]=useState(false);
 const [isEluFocusMode,setIsEluFocusMode]=useState<boolean>(()=>localStorage.getItem('mayortech_focus_elu_mode')==='true');
 const [delegation,setDelegation]=useState<{active:boolean;delegate:string}>(()=>{
  try{const s=localStorage.getItem('mayortech_absence_delegation');return s?JSON.parse(s):{active:false,delegate:''};}catch{return {active:false,delegate:''};}
 });
 useEffect(()=>{
  const handleDel=(e:Event)=>{if(e instanceof CustomEvent&&e.detail){setDelegation({active:e.detail.active,delegate:e.detail.delegate});}};
  const handleFocus=(e:Event)=>{if(e instanceof CustomEvent&&typeof e.detail?.active==='boolean'){setIsEluFocusMode(e.detail.active);}};
  const handleOpenPal=()=>setIsPaletteOpen(true);
  const handleOpenDel=()=>setIsDelegationOpen(true);
  window.addEventListener('mayortech:delegation-changed',handleDel);
  window.addEventListener('mayortech:focus-elu-changed',handleFocus);
  window.addEventListener('mayortech:open-palette',handleOpenPal);
  window.addEventListener('mayortech:open-delegation',handleOpenDel);
  return ()=>{
   window.removeEventListener('mayortech:delegation-changed',handleDel);
   window.removeEventListener('mayortech:focus-elu-changed',handleFocus);
   window.removeEventListener('mayortech:open-palette',handleOpenPal);
   window.removeEventListener('mayortech:open-delegation',handleOpenDel);
  };
 },[]);
 const viewLocation=useLocation(),path=viewLocation.pathname;const [collapsed,setCollapsed]=useState(false),[mobileOpen,setMobileOpen]=useState(false),[appearance,setAppearance]=useState(getAppearance()),[profilePending,setProfilePending]=useState(false),[profileError,setProfileError]=useState('');const aside=useRef<HTMLElement>(null),menu=useRef<HTMLButtonElement>(null);
 const routeProject=/^\/(?:chantiers|project)\/([^/]+)/.exec(path)?.[1];const currentProjectId=state.projects.find(project=>project.id===routeProject)?.id;
 const mailbox=path==='/messagerie'||path.startsWith('/mail');
 const identity=workspaceMailIdentity(session);
 const [inboxCounter,setInboxCounter]=useState<{identity:string;messages:typeof state.messages;unread:number}|null>(null);
 useEffect(()=>{const updated=(event:Event)=>{if(!(event instanceof CustomEvent))return;const count=mailFolderUnread(event.detail,identity);if(count!==null)setInboxCounter({identity,messages:state.messages,unread:count});};window.addEventListener('travaux:mail-folders',updated);return()=>window.removeEventListener('travaux:mail-folders',updated);},[identity,state.messages]);
 const unread=inboxCounter?.identity===identity&&inboxCounter.messages===state.messages?inboxCounter.unread:state.messages.filter(message=>!message.read&&message.folder==='inbox').length;
 useEffect(()=>{applyWorkspaceAppearance();},[]);
 useEffect(()=>{setMobileOpen(false);window.scrollTo({top:0});},[viewLocation.href]);
 useEffect(()=>{const handler=()=>setAppearance(getAppearance());window.addEventListener('travaux:appearance',handler);return()=>window.removeEventListener('travaux:appearance',handler);},[]);
 useEffect(()=>{const mq=window.matchMedia('(max-width:640px)');const update=()=>{if(aside.current)aside.current.inert=mq.matches&&!mobileOpen;};update();mq.addEventListener('change',update);return()=>mq.removeEventListener('change',update);},[mobileOpen]);
 useEffect(()=>{if(mobileOpen)aside.current?.querySelector<HTMLButtonElement>('button')?.focus();const key=(event:KeyboardEvent)=>{if(!mobileOpen)return;if(event.key==='Escape'){setMobileOpen(false);requestAnimationFrame(()=>menu.current?.focus());}if(event.key==='Tab'){const controls=Array.from(aside.current?.querySelectorAll<HTMLElement>('a,button,select')||[]).filter(x=>x.offsetWidth);const first=controls[0],last=controls.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[mobileOpen]);
 const palette=palettes.find((p:any)=>p.id===appearance.color)||palettes[0];
 const tokens={'--primary':palette.accent,'--accent':palette.soft,'--green':palette.accent,'--green-deep':palette.hover,'--green-light':palette.soft,'--ink':'var(--foreground)','--line':'var(--border)','--surface':'var(--background)'} as CSSProperties;
 if(path.startsWith('/quick-sign')){return <div className="min-h-screen bg-slate-50 flex items-center justify-center p-2 sm:p-4" style={tokens}>{children}</div>;}
 const pending=bootstrap?.stats?.pending_reviews||0;const favorites=state.projects.filter(p=>p.favorite);const shown=favorites.length?favorites:state.projects.slice(0,4);
 const dossierLabel=commissionCfg.hasChantiers?'Chantiers':'Dossiers';
 async function changeProfile(id:string){if(profilePending||id===activeCommissionId)return;setProfilePending(true);setProfileError('');try{await setActiveCommissionId(id);window.location.hash='/';setMobileOpen(false);}catch(cause){setProfileError(cause instanceof Error?cause.message:'Enregistrez vos modifications avant de changer de profil.');}finally{setProfilePending(false);}}
 if(isEluFocusMode){
  return <div className="min-h-screen bg-[#F7F7F5] text-stone-900 font-sans flex flex-col" style={tokens}>
   <header className="h-14 bg-white border-b border-stone-200/90 px-4 sm:px-6 flex items-center justify-between shadow-[0_1px_2px_rgba(16,42,76,0.04)] sticky top-0 z-40">
    <div className="flex items-center gap-3">
     <Link to="/" className="brand flex items-center gap-2 font-bold text-stone-900 tracking-tight"><span className="brand-mark bg-[#102A4C] text-white"><Landmark size={20}/></span><span>MayorTech<span className="text-[#102A4C]">.</span></span></Link>
     <span className="hidden sm:inline-block text-[11px] font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-2.5 py-0.5 rounded-full">Vue Simplifiée Élu</span>
    </div>
    <div className="flex items-center gap-1 sm:gap-2 text-xs">
     <Link to="/workflows" className={`px-3 py-1.5 rounded-md font-bold flex items-center gap-1.5 transition-colors ${path.startsWith('/workflows')?'bg-[#102A4C] text-white shadow-xs':'text-stone-700 hover:bg-stone-100'}`}><CheckCircle2 size={15}/><span>À signer (3)</span></Link>
     <Link to="/agenda" className={`px-3 py-1.5 rounded-md font-bold flex items-center gap-1.5 transition-colors ${path==='/agenda'?'bg-[#102A4C] text-white shadow-xs':'text-stone-700 hover:bg-stone-100'}`}><CalendarDays size={15}/><span className="hidden sm:inline">Agenda & Séances</span></Link>
     <Link to="/dossiers" className={`px-3 py-1.5 rounded-md font-bold flex items-center gap-1.5 transition-colors ${path==='/dossiers'||path==='/chantiers'?'bg-[#102A4C] text-white shadow-xs':'text-stone-700 hover:bg-stone-100'}`}><HardHat size={15}/><span className="hidden sm:inline">Dossiers suivis</span></Link>
    </div>
    <div className="flex items-center gap-2">
     <Button variant="outline" size="sm" onClick={()=>{setIsEluFocusMode(false);localStorage.setItem('mayortech_focus_elu_mode','false');window.dispatchEvent(new CustomEvent('mayortech:focus-elu-changed',{detail:{active:false}}));}} className="text-xs font-semibold text-stone-700 rounded-md flex items-center gap-1.5 border-stone-200 hover:bg-stone-100 shadow-3xs cursor-pointer"><PanelLeftOpen size={14}/><span className="hidden sm:inline">Revenir à la vue complète</span><span className="sm:hidden">Quitter</span></Button>
    </div>
   </header>
   <main className="flex-1 p-3 sm:p-6 max-w-7xl w-full mx-auto">{children}</main>
   <CommandPaletteModal isOpen={isPaletteOpen} onClose={()=>setIsPaletteOpen(false)}/>
  </div>;
 }

 return <div className={`workspace ${collapsed?'nav-collapsed':''} ${mobileOpen?'mobile-open':''}`} style={tokens}>
 {mobileOpen&&<button className="nav-scrim" aria-label="Fermer la navigation" onClick={()=>{setMobileOpen(false);requestAnimationFrame(()=>menu.current?.focus());}}/>}
 <aside ref={aside} className="sidebar flex flex-col h-screen" aria-label="Navigation principale">
  <Button className="close-mobile" variant="ghost" size="icon" aria-label="Fermer la navigation" onClick={()=>{setMobileOpen(false);requestAnimationFrame(()=>menu.current?.focus());}}><X/></Button>
  <Link to="/" className="brand"><span className="brand-mark bg-[#102A4C] text-white"><Landmark size={20}/></span>MayorTech<span className="brand-dot text-[#102A4C]">.</span></Link>
  
  <div className="flex-1 overflow-y-auto pr-0.5 space-y-1">
   <div className="org-switch-wrapper relative px-2 py-1">
    <div onClick={()=>setIsOrgMenuOpen(!isOrgMenuOpen)} className="org-switch cursor-pointer select-none border-stone-200">
     <span className="org-mark">{(organization?.name||state.organization||'E').slice(0,1)}</span>
     <div className="min-w-0 flex-1">
      <strong className="truncate block max-w-[130px]">{organization?.name||state.organization||'Espace de démonstration'}</strong>
      <small>Collectivité locale</small>
     </div>
     <ChevronDown size={15}/>
    </div>
    {isOrgMenuOpen&&(
     <div className="absolute top-full left-2 right-2 mt-1 bg-white border border-stone-200 rounded-lg shadow-lg p-1.5 z-50 text-xs animate-in fade-in duration-100">
      <Link to="/parametres" search={{section:'modules'} as any} className="flex items-center gap-2 p-2 rounded-md hover:bg-stone-50 text-stone-700 font-medium transition-colors" onClick={()=>setIsOrgMenuOpen(false)}>
       <Settings size={14} className="text-stone-500"/><span>Modules & Périmètre</span>
      </Link>
      <button type="button" onClick={()=>{setIsOrgMenuOpen(false);setIsWizardOpen(true);}} className="w-full flex items-center gap-2 p-2 rounded-md hover:bg-stone-100 text-[#102A4C] font-semibold transition-colors cursor-pointer text-left">
       <Plus size={14} className="text-[#102A4C]"/><span>+ Nouvelle organisation</span>
      </button>
     </div>
    )}
   </div>
   {(commissions.length>0||state.projects.length>0)&&<div className="commission-selector px-3 py-2 border-b border-border/40"><label htmlFor="sidebar-commission-select" className="text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500 block mb-1">Profil de travail</label><select id="sidebar-commission-select" aria-label="Changer de profil de travail" value={activeCommissionId} disabled={profilePending} onChange={e=>void changeProfile(e.target.value)} style={{borderLeft: `3px solid ${commissionCfg.accentColor}`}} className="w-full text-xs font-semibold bg-white border border-stone-200 rounded-md py-1.5 px-2 text-stone-800 cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#102A4C] whitespace-normal shadow-3xs"><option value="all">0. Direction Générale (Vue transversale)</option>{visibleCommissions.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>{activeCommission&&<div className="flex items-center gap-1.5 mt-1.5 text-[11px]"><span className={`inline-block w-2 h-2 rounded-full ${activeCommission.can_edit?'bg-emerald-500':'bg-amber-500'}`}/><span className="text-stone-500 truncate">{commissionCfg.poleLabel}</span>{!activeCommission.can_edit&&<span className="ml-auto text-[10px] bg-amber-500/15 text-amber-700 font-semibold px-1 py-0.5 rounded">Lecture seule</span>}</div>}{profileError&&<p className="form-error" role="alert">{profileError}</p>}</div>}
   <nav className="main-nav">
    <Link to="/" className={path==='/'||path==='/today'?'active':''}><Sun size={19}/>Accueil</Link>
    <Link to="/workflows" className={path.startsWith('/workflows')||path.startsWith('/processus')?'active':''}><CheckCircle2 size={19}/>Validations<span className="nav-count tabular-nums">{commissionCfg.allowedDossierIds.length}</span></Link>
    {hasModule('messagerie_eml')&&<Link to="/messagerie" className={mailbox?'active':''}><Mail size={19}/>Messagerie<span className="nav-count tabular-nums">{unread||''}</span></Link>}
    <Link to="/dossiers" className={path==='/dossiers'||path.startsWith('/chantiers')||path.startsWith('/project')?'active':''}>
     {commissionCfg.hasChantiers ? <HardHat size={19}/> : <FileText size={19}/>}
     {dossierLabel}
     <span className="nav-count tabular-nums">{commissionCfg.hasChantiers ? state.projects.length : commissionCfg.allowedDossierIds.length}</span>
    </Link>
    <Link to="/actions" className={path==='/actions'||path.startsWith('/review')?'active':''}><CheckCheck size={19}/>Tâches & Suivi</Link>
    
    <div className="nav-label text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500">{commissionCfg.sidebarSection.title}</div>
    {commissionCfg.sidebarSection.items.map((item, idx) => (
     <Link key={idx} to={item.to as any} className={path===item.to?'active':''}>
      {item.iconName==='chart'&&<ChartNoAxesGantt size={19}/>}
      {item.iconName==='clipboard'&&<ClipboardCheck size={19}/>}
      {item.iconName==='calendar'&&<CalendarDays size={19}/>}
      {item.iconName==='coins'&&<Coins size={19}/>}
      {item.iconName==='file-text'&&<FileText size={19}/>}
      {item.iconName==='landmark'&&<Landmark size={19}/>}
      {item.iconName==='users'&&<Users size={19}/>}
      {item.iconName==='heart'&&<Heart size={19}/>}
      {item.iconName==='building'&&<Building2 size={19}/>}
      {item.iconName==='map'&&<MapPin size={19}/>}
      <span>{item.label}</span>
      {item.badge&&<span className="nav-count tabular-nums">{item.badge}</span>}
     </Link>
    ))}
   </nav>
   {commissionCfg.hasChantiers ? (
    <>
     <div className="nav-label text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500">{favorites.length?'CHANTIERS FAVORIS':'CHANTIERS'} <Star size={12}/></div>
     <nav className="favorites">{shown.map(p=><Link key={p.id} to="/chantiers/$id" params={{id:p.id}}><span className={`project-dot ${p.status==='En cours'?'green':'amber'}`}/>{p.title}</Link>)}</nav>
    </>
   ) : commissionCfg.pinnedBlock ? (
    <>
     <div className="nav-label text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500">{commissionCfg.pinnedBlock.title}</div>
     <div className="px-2 py-1 space-y-1">
      {commissionCfg.pinnedBlock.items.map((pi, pidx) => (
       <a key={pidx} href="#/workflows" className="block p-1.5 rounded-md hover:bg-stone-100 text-stone-700 transition-colors">
        <div className="flex items-center justify-between text-xs font-semibold">
         <span className="truncate">{pi.label}</span>
         {pi.tag && <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-stone-200 text-stone-700 shrink-0">{pi.tag}</span>}
        </div>
        {pi.sub && <small className="text-[10px] text-stone-500 block truncate">{pi.sub}</small>}
       </a>
      ))}
     </div>
    </>
   ) : null}
  </div>

  <div className="sidebar-bottom pt-2 border-t border-stone-200">
    {delegation.active && (
     <div className="mx-2 mb-2 p-2 bg-amber-50 border border-amber-200/80 rounded-md text-[10px] text-amber-900 font-semibold flex items-center gap-1.5 shadow-2xs">
      <UserCheck className="w-3.5 h-3.5 text-amber-700 shrink-0" />
      <span className="truncate">Suppléance active &rarr; {delegation.delegate.split('·')[0].trim()}</span>
     </div>
    )}
    <button type="button" onClick={()=>setIsDelegationOpen(true)} className="flex items-center gap-2 px-3 py-1.5 mx-2 text-xs text-stone-700 hover:bg-stone-100 rounded-md transition-colors cursor-pointer text-left w-auto mb-1">
     <UserCheck size={16} className="text-amber-600"/>
     <span>Absence & Suppléant</span>
    </button>
    <Link to="/parametres" className={path.includes('parametres')||path.includes('settings')?'settings-link active':'settings-link'}><Settings size={18}/>Paramètres</Link><WorkspaceLogout/>{session?.demo&&session?.auth_required!==true&&<div className="demo-label"><FlaskConical size={15}/><span>Mode démonstration</span></div>}<a href="#/parametres?section=members" className="profile flex items-center gap-2.5 p-2 border-t border-stone-200"><span className="avatar small font-bold" style={{backgroundColor: commissionCfg.accentColor + '18', color: commissionCfg.accentColor}}>{commissionCfg.avatarInitials}</span><div className="min-w-0 flex-1"><strong className="text-xs font-semibold text-stone-900 block truncate">{commissionCfg.greetingName} ({commissionCfg.shortName})</strong><small className="text-[10px] text-stone-500 block truncate">{commissionCfg.poleLabel}</small></div><ChevronDown size={14}/></a></div></aside>
  <div className="workspace-main" inert={mobileOpen?true:undefined}>
  <header className="topbar">
   <div className="breadcrumb">
    <Button ref={menu} className="mobile-menu" variant="ghost" size="icon" aria-label="Ouvrir la navigation" aria-expanded={mobileOpen} onClick={()=>setMobileOpen(true)}><Menu/></Button>
    <Button className="collapse-menu" variant="ghost" size="icon" aria-label={collapsed?'Afficher la navigation':'Réduire la navigation'} onClick={()=>setCollapsed(!collapsed)}><PanelLeftClose/></Button>
    <span>{activeCommission?(activeCommission.name.split('.')[1]?.trim()||activeCommission.name):'Travaux'}</span>
    <span className="crumb-separator">/</span>
    <strong>{path==='/'||path==='/today'?'Accueil':mailbox?'Messagerie':path.startsWith('/workflows')||path.startsWith('/processus')?'Circuits de validation':path==='/planning'?'Planning':path==='/terrain'?'Suivi terrain':path==='/agenda'?'Agenda':path==='/assistant'?'Assistant':path==='/connexion'?'Première connexion':path==='/connexions'?'Connexions':path==='/actions'?'Tâches & Suivi':path.includes('parametres')||path.includes('settings')?'Paramètres':path.startsWith('/review')?'Tâches & Suivi':dossierLabel}</strong>
    {activeCommission&&!activeCommission.can_edit&&<span className="ml-2 inline-flex items-center text-xs bg-amber-500/15 text-amber-700 dark:text-amber-300 font-medium px-2 py-0.5 rounded border border-amber-500/25">Lecture seule</span>}
   </div>

   {/* Universal Ctrl+K search trigger in header */}
   <div className="hidden md:flex items-center justify-center flex-1 max-w-sm mx-4">
    <button
      type="button"
      onClick={()=>setIsPaletteOpen(true)}
      className="w-full flex items-center justify-between px-3 py-1.5 bg-slate-100 hover:bg-slate-200/70 border border-slate-200 rounded-xl text-xs text-slate-500 transition-colors shadow-3xs cursor-pointer"
      title="Recherche universelle (Ctrl+K)"
    >
      <span className="flex items-center gap-2 truncate">
        <Search size={14} className="text-slate-400 shrink-0" />
        <span className="truncate">Rechercher un dossier, arrêté, agent...</span>
      </span>
      <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-mono font-bold text-slate-500 shadow-3xs shrink-0 ml-2">
        Ctrl K
      </kbd>
    </button>
   </div>

   <div className="topbar-end">
    <Button variant="ghost" size="icon" className="md:hidden text-slate-600 mr-1" onClick={()=>setIsPaletteOpen(true)} aria-label="Recherche rapide"><Search size={17}/></Button>
    <Button variant="ghost" size="sm" onClick={()=>{setIsEluFocusMode(true);localStorage.setItem('mayortech_focus_elu_mode','true');window.dispatchEvent(new CustomEvent('mayortech:focus-elu-changed',{detail:{active:true}}));}} className="hidden sm:flex items-center gap-1.5 text-xs text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-xl mr-2 font-semibold cursor-pointer"><Sparkles size={13} className="text-amber-500"/><span>Focus Élu</span></Button>
    <a className="avatar small" href="#/parametres?section=members" aria-label="Mon accès">{session?.public_demo?'V':'ST'}</a>
   </div>
  </header>
  {workProfileNotice&&<p className="work-profile-notice" role="status">{workProfileNotice}</p>}
  {children}
  <nav className="mobile-nav" aria-label="Navigation rapide">
   <Link to="/"><Sun size={20}/><span>Accueil</span></Link>
   <Link to="/workflows" className="relative"><CheckCircle2 size={20}/><span>À valider</span><span className="absolute -top-1 right-2 bg-blue-600 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center shadow-3xs">3</span></Link>
   <Link to="/dossiers"><HardHat size={20}/><span>{dossierLabel}</span></Link>
   {hasModule('messagerie_eml')&&<Link to="/messagerie"><Mail size={20}/><span>Messages</span></Link>}
   <Link to="/actions"><CheckCheck size={20}/><span>Tâches</span></Link>
  </nav>
 </div>
 {hasModule('ai_assistant')&&<AssistantWidget projectId={currentProjectId}/>}
 <OrganizationCreationWizardModal isOpen={isWizardOpen} onClose={()=>setIsWizardOpen(false)}/>
 <AbsenceDelegationModal isOpen={isDelegationOpen} onClose={()=>setIsDelegationOpen(false)} onDelegationChange={(active, delegate)=>setDelegation({active, delegate})}/>
 <CommandPaletteModal isOpen={isPaletteOpen} onClose={()=>setIsPaletteOpen(false)} onOpenValidationLaunch={()=>{setIsPaletteOpen(false);window.location.hash='/workflows?launch=1';}} onOpenDelegation={()=>{setIsPaletteOpen(false);setIsDelegationOpen(true);}}/>
</div>;
}
