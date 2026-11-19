import React, { useState } from 'react';
import { ShieldCheck, KeyRound, Building2, UserCheck, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MunicipalJoinSasModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function MunicipalJoinSasModal({ isOpen, onClose, onSuccess }: MunicipalJoinSasModalProps) {
  const [code, setCode] = useState('');
  const [nom, setNom] = useState('');
  const [prenom, setPrenom] = useState('');
  const [email, setEmail] = useState('');
  const [poste, setPoste] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/organization/join-requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux'
        },
        body: JSON.stringify({
          code_organisation: code.trim(),
          nom: nom.trim(),
          prenom: prenom.trim(),
          email: email.trim().toLowerCase(),
          poste_souhaite: poste.trim()
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error?.message || 'Erreur lors de la soumission de la demande.');
      }

      setSuccess(true);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || 'Code confidentiel invalide ou service indisponible.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 border border-slate-100 space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between border-b pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Sas d'Enrôlement Municipal
              </h2>
              <p className="text-xs text-slate-500">
                Ville de Plougastel-Daoulas · Espace Sécurisé
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 font-bold p-1 rounded"
          >
            ✕
          </button>
        </div>

        {success ? (
          <div className="space-y-4 py-3 text-center">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h3 className="font-bold text-slate-900 text-base">Demande transmise avec succès</h3>
              <p className="text-xs text-slate-600">
                Votre demande a été placée dans la file d'attente de la Direction Générale des Services (DGS). Vous recevrez confirmation de votre habilitation et commission d'affectation dès validation.
              </p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg text-xs text-blue-800 text-left flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 flex-shrink-0 text-blue-600 mt-0.5" />
              <span>
                N'oubliez pas d'enrôler votre application <strong>TOTP 2FA</strong> (FreeOTP ou Google Authenticator) pour sceller vos futures connexions.
              </span>
            </div>
            <Button onClick={onClose} className="w-full">
              Fermer le Sas
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 text-sm">
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg flex items-center gap-2 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Code Confidentiel Municipal d'Adhésion :
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  required
                  value={code}
                  onChange={e => setCode(e.target.value)}
                  placeholder="ex: PLOUGASTEL-2026"
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 font-mono tracking-wider uppercase font-bold text-slate-900 bg-white"
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Code délivré par la DGS ou le service des Ressources Humaines.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Nom :</label>
                <input
                  type="text"
                  required
                  value={nom}
                  onChange={e => setNom(e.target.value)}
                  placeholder="ex: DUPONT"
                  className="w-full p-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 uppercase text-slate-900 bg-white font-medium"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Prénom :</label>
                <input
                  type="text"
                  required
                  value={prenom}
                  onChange={e => setPrenom(e.target.value)}
                  placeholder="ex: Marie"
                  className="w-full p-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 capitalize text-slate-900 bg-white font-medium"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Courriel Professionnel (@ville-plougastel.bzh) :
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="prenom.nom@ville-plougastel.bzh"
                className="w-full p-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 text-slate-900 bg-white font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Poste ou Mandat Municipal :
              </label>
              <input
                type="text"
                required
                value={poste}
                onChange={e => setPoste(e.target.value)}
                placeholder="ex: Instructeur Droit des Sols, Adjoint..."
                className="w-full p-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 text-slate-900 bg-white font-medium"
              />
            </div>

            <div className="p-3 bg-slate-50 border rounded-lg text-xs text-slate-600 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Sécurité renforcée :</strong> La validation humaine par la DGS est requise avant tout déblocage d'accès aux dossiers des commissions.
              </span>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button 
                type="button" 
                variant="outline" 
                onClick={onClose} 
                disabled={loading}
                className="text-slate-700 border-slate-300 hover:bg-slate-100 font-medium"
              >
                Annuler
              </Button>
              <Button type="submit" disabled={loading} className="bg-blue-700 hover:bg-blue-800 text-white font-medium shadow-sm">
                {loading ? 'Vérification...' : 'Soumettre ma Demande'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
