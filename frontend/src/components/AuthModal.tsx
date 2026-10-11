import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Lock, User, KeyRound, ShieldAlert, X, Info } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const { isLoginModalOpen, closeLoginModal, login, authError, clearError } = useAuth();
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isLoginModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password) return;

    setIsSubmitting(true);
    const success = await login(usernameOrEmail.trim(), password);
    setIsSubmitting(false);
    if (success) {
      setPassword('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl shadow-cyan-950/20">
        {/* Close Button */}
        <button
          onClick={closeLoginModal}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-800"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-900/30">
            <Lock className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">Private Platform Access</h2>
            <p className="text-xs text-slate-400">Sign in with your authorized credentials</p>
          </div>
        </div>

        {/* Error Alert */}
        {authError && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
            <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">{authError}</p>
            </div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Username or Email
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <User className="w-4 h-4" />
              </div>
              <input
                type="text"
                required
                value={usernameOrEmail}
                onChange={(e) => {
                  setUsernameOrEmail(e.target.value);
                  if (authError) clearError();
                }}
                placeholder="admin or name@company.com"
                className="w-full pl-9 pr-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <KeyRound className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (authError) clearError();
                }}
                placeholder="••••••••••••"
                className="w-full pl-9 pr-10 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors font-mono"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs text-slate-500 hover:text-slate-300"
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !usernameOrEmail.trim() || !password}
            className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-lg shadow-lg shadow-cyan-900/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        {/* Private Access Notice */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-start gap-2.5 text-[11px] text-slate-400">
          <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <p>
            <strong className="text-slate-300">Private Access Protocol:</strong> Unrestricted public registration is disabled. Only explicitly authorized testing accounts provisioned by the system administrator may access private analytics and exchange connections.
          </p>
        </div>
      </div>
    </div>
  );
};
