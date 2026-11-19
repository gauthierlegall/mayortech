// Keep the existing device preference, mapped to the Lovable semantic tokens.
// @ts-ignore The audited shared module is intentionally framework-neutral JS.
import {getAppearance, palettes, setAppearance} from '../../../../web/appearance.js';

export interface Appearance {color:string; density:'compact'|'comfortable'}
export interface Palette {id:string; name:string; accent:string; hover:string; soft:string}
export const workspacePalettes=palettes as readonly Palette[];
export const getWorkspaceAppearance=()=>getAppearance() as Appearance;

export function applyWorkspaceAppearance(value:Appearance=getWorkspaceAppearance()){
 const palette=workspacePalettes.find(item=>item.id===value.color)??workspacePalettes[0]!;
 document.documentElement.dataset.palette=palette.id;
 document.documentElement.dataset.density=value.density;
 const tokens={'--primary':palette.accent,'--accent':palette.soft,'--accent-hover':palette.hover,'--accent-soft':palette.soft,'--travaux-primary':palette.accent,'--travaux-soft':palette.soft};
 for(const node of [document.documentElement,...document.querySelectorAll<HTMLElement>('.workspace')]){
  for(const [key,color] of Object.entries(tokens))node.style.setProperty(key,color);
 }
 return value;
}

export function saveWorkspaceAppearance(change:Partial<Appearance>){
 const value=setAppearance(change) as Appearance;
 applyWorkspaceAppearance(value);
 window.dispatchEvent(new CustomEvent('travaux:appearance',{detail:value}));
 return value;
}
