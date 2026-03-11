import { useState, useEffect } from 'react';
import './index.css';
import type { Target, Narrative } from './api';
import { fetchTargets, fetchNarratives } from './api';
import StepIndicator from './components/StepIndicator';
import TargetSelector from './components/TargetSelector';
import NarrativeSelector from './components/NarrativeSelector';
import GenerationPanel from './components/GenerationPanel';

const STEPS = ['Select Target', 'Select Narrative', 'Generate'];

export default function App() {
  const [step, setStep] = useState(1);
  const [targets, setTargets] = useState<Target[]>([]);
  const [narratives, setNarratives] = useState<Narrative[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [selectedNarrative, setSelectedNarrative] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [t, n] = await Promise.all([fetchTargets(), fetchNarratives()]);
      setTargets(t);
      setNarratives(n);
      setBackendError(false);
    } catch {
      setBackendError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleTargetSelect = (id: string) => {
    setSelectedTarget(id);
    setTimeout(() => setStep(2), 300);
  };

  const handleNarrativeSelect = (id: string) => {
    setSelectedNarrative(id);
    setTimeout(() => setStep(3), 300);
  };

  const handleReset = () => {
    setStep(1);
    setSelectedTarget(null);
    setSelectedNarrative(null);
  };

  const selectedTargetObj = targets.find(t => t.id === selectedTarget);
  const selectedNarrativeObj = narratives.find(n => n.id === selectedNarrative);

  return (
    <div className="min-h-screen bg-surface-900">
      {/* Background effect */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-brand-500/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] bg-accent-500/5 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="border-b border-surface-700/50 backdrop-blur-md bg-surface-900/80 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-400 to-accent-500 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-brand-500/25">
              🛡️
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-primary tracking-tight">
                Misinfo Generator
              </h1>
              <p className="text-[10px] text-text-muted uppercase tracking-widest">
                AI Detection Showcase Demo
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {step > 1 && (
              <button
                id="back-btn"
                onClick={() => setStep(step - 1)}
                className="flex items-center gap-1.5 text-text-secondary hover:text-text-primary text-sm transition-colors cursor-pointer"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>
            )}
            <div className="hidden sm:flex items-center gap-2 bg-surface-800 rounded-lg px-3 py-1.5 border border-surface-600">
              <div className={`w-2 h-2 rounded-full ${backendError ? 'bg-red-400' : 'bg-green-400'}`} />
              <span className="text-xs text-text-muted">{backendError ? 'Backend Offline' : 'Backend Connected'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <StepIndicator currentStep={step} steps={STEPS} />

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-3 border-brand-400/20 border-t-brand-400 rounded-full animate-spin" />
              <p className="text-text-secondary text-sm">Connecting to backend...</p>
            </div>
          </div>
        ) : backendError ? (
          <div className="max-w-lg mx-auto">
            <div className="glass-card p-8 text-center">
              <span className="text-4xl mb-4 block">⚠️</span>
              <h2 className="text-xl font-bold text-text-primary mb-2">Backend Not Running</h2>
              <p className="text-text-secondary text-sm mb-6">
                Make sure the FastAPI backend is running on <code className="text-brand-300 bg-surface-800 px-2 py-0.5 rounded">localhost:8000</code>
              </p>
              <div className="bg-surface-800 rounded-xl p-4 text-left text-xs font-mono text-text-muted mb-6">
                <p className="text-text-secondary mb-1"># Start the backend:</p>
                <p>cd backend</p>
                <p>pip install -r requirements.txt</p>
                <p>uvicorn main:app --reload --port 8000</p>
              </div>
              <button
                onClick={loadData}
                className="px-6 py-2.5 bg-brand-500 hover:bg-brand-400 text-white rounded-lg font-semibold text-sm transition-colors cursor-pointer"
              >
                Retry Connection
              </button>
            </div>
          </div>
        ) : (
          <>
            {step === 1 && (
              <TargetSelector
                targets={targets}
                selectedTarget={selectedTarget}
                onSelect={handleTargetSelect}
              />
            )}

            {step === 2 && (
              <NarrativeSelector
                narratives={narratives}
                selectedNarrative={selectedNarrative}
                onSelect={handleNarrativeSelect}
              />
            )}

            {step === 3 && selectedTargetObj && selectedNarrativeObj && (
              <GenerationPanel
                key={`${selectedTarget}-${selectedNarrative}`}
                target={selectedTargetObj}
                narrative={selectedNarrativeObj}
                onReset={handleReset}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-700/30 py-6 mt-10">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-text-muted text-xs">
            🛡️ SUTD AI Misinformation Detection System — Showcase Demo
          </p>
          <p className="text-text-muted text-xs">
            For educational and demonstration purposes only
          </p>
        </div>
      </footer>
    </div>
  );
}
