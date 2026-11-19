export type ProjectView='projects'|'arbitration'|'map'|'agenda'|'actions';
export interface CommissionPresentation {
  title:string;
  views:ProjectView[];
  defaultView:ProjectView;
  properties:string;
  propertyOrder:string[];
}
export function presentationForCommission(commissionId:string):CommissionPresentation;
export function projectViewForCommission(commissionId:string,requested:string|null):ProjectView;
export function orderPropertyFields<T extends {key:string}>(fields:T[],commissionId:string):T[];
