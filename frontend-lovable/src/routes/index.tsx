import {createFileRoute} from '@tanstack/react-router';
import {workspaceOptions} from '@/features/workspace/data';
import {WorkspaceProvider} from '@/features/workspace/context';
import {Shell} from '@/features/workspace/Shell';
import {Projects} from '@/features/workspace/Projects';
import {pageMeta} from '@/features/workspace/route-meta';
export const Route=createFileRoute('/')({head:()=>pageMeta('Chantiers','MayorTech : dossiers de chantier, échanges et prochaines actions de la collectivité.'),loader:({context})=>context.queryClient.ensureQueryData(workspaceOptions),component:Index});
function Index(){return <WorkspaceProvider><Shell><Projects/></Shell></WorkspaceProvider>;}
