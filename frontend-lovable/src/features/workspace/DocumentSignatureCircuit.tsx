import {useEffect, useState} from 'react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';

const labels = {
  not_started: 'Soumettez cet original à un autre membre habilité avant la signature.',
  review: 'En attente de relecture par un autre membre habilité.',
  rejected: 'Validation refusée.',
  awaiting_signature: 'PDF validé. La signature reste à recueillir.',
};

type Circuit = {
  status: keyof typeof labels;
  revision: number;
  can_submit: boolean;
  can_decide: boolean;
};

export function DocumentSignatureCircuit({projectId, documentId, sha256}: {
  projectId: string; documentId: string; sha256: string;
}) {
  const {api} = useWorkspace();
  const [circuit, setCircuit] = useState<Circuit | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    api.signatureCircuit(projectId, documentId).then((state: Circuit) => {
      if (active) setCircuit(state);
    }).catch(() => {
      if (active) setError('Le circuit n’a pas pu être chargé.');
    });
    return () => { active = false; };
  }, [api, projectId, documentId, reload]);

  async function update(decision?: 'approve' | 'reject') {
    if (!circuit || busy) return;
    setBusy(true);
    setError('');
    try {
      const state = decision
        ? await api.reviewSignatureCircuit(projectId, documentId, {decision, revision: circuit.revision})
        : await api.submitSignatureCircuit(projectId, documentId, {document_sha256: sha256});
      setCircuit(state);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'La décision n’a pas été enregistrée.');
    } finally {
      setBusy(false);
    }
  }

  return <section className="source-callout" aria-label="Circuit de signature">
    <h3>Circuit de signature</h3>
    <p role="status">{circuit ? labels[circuit.status] : error ? '' : 'Chargement du circuit…'}</p>
    {error && <div>
      <p role="alert">{error}</p>
      <Button variant="link" onClick={() => { setError(''); setReload(value => value + 1); }}>Recharger le circuit</Button>
    </div>}
    <div className="flex flex-wrap gap-2">
      {circuit?.can_submit && <Button variant="outline" disabled={busy} onClick={() => void update()}>Soumettre pour validation</Button>}
      {circuit?.can_decide && <>
        <Button disabled={busy} onClick={() => void update('approve')}>Valider pour signature</Button>
        <Button variant="outline" disabled={busy} onClick={() => void update('reject')}>Refuser la validation</Button>
      </>}
    </div>
  </section>;
}
