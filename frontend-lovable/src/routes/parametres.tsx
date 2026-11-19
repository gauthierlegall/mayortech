import {createFileRoute} from '@tanstack/react-router';
import {workspaceOptions} from '@/features/workspace/data';
import {WorkspaceProvider} from '@/features/workspace/context';
import {Shell} from '@/features/workspace/Shell';
import {Settings} from '@/features/workspace/Settings';
import {pageMeta} from '@/features/workspace/route-meta';
export const Route=createFileRoute('/parametres')({head:()=>pageMeta('Paramètres','Apparence, organisation et connexions de l’espace municipal MayorTech.'),loader:({context})=>context.queryClient.ensureQueryData(workspaceOptions),component:SettingsPage});
function SettingsPage(){return <WorkspaceProvider><Shell><Settings/></Shell></WorkspaceProvider>;}
