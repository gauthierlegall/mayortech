import {createFileRoute} from '@tanstack/react-router';
import {workspaceOptions} from '@/features/workspace/data';
import {WorkspaceProvider} from '@/features/workspace/context';
import {Shell} from '@/features/workspace/Shell';
import {Mail} from '@/features/workspace/Mail';
import {pageMeta} from '@/features/workspace/route-meta';
export const Route=createFileRoute('/messagerie')({head:()=>pageMeta('Messagerie','Conversations et messages liés aux chantiers dans la démonstration MayorTech.'),loader:({context})=>context.queryClient.ensureQueryData(workspaceOptions),component:MailPage});
function MailPage(){return <WorkspaceProvider><Shell><Mail/></Shell></WorkspaceProvider>;}
