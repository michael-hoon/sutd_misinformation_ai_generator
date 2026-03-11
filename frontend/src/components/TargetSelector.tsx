import type { Target } from '../api';

interface TargetSelectorProps {
  targets: Target[];
  selectedTarget: string | null;
  onSelect: (id: string) => void;
}

const categoryIcons: Record<string, string> = {
  politician: '🏛️',
  celebrity: '⭐',
};

const categoryColors: Record<string, string> = {
  politician: 'from-brand-500/20 to-brand-700/10',
  celebrity: 'from-accent-500/20 to-accent-600/10',
};

export default function TargetSelector({ targets, selectedTarget, onSelect }: TargetSelectorProps) {
  const politicians = targets.filter(t => t.category === 'politician');
  const celebrities = targets.filter(t => t.category === 'celebrity');

  const renderGrid = (items: Target[], label: string) => (
    <div className="mb-8">
      <h3 className="text-sm uppercase tracking-widest text-text-muted mb-4 font-semibold">
        {label}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {items.map((target, i) => (
          <button
            id={`target-${target.id}`}
            key={target.id}
            onClick={() => onSelect(target.id)}
            className={`glass-card p-5 text-left cursor-pointer animate-slide-up ${
              selectedTarget === target.id ? 'selected' : ''
            }`}
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${categoryColors[target.category] || ''} flex items-center justify-center text-2xl mb-3`}>
              {categoryIcons[target.category] || '👤'}
            </div>
            <h4 className="text-text-primary font-semibold text-base mb-1">{target.name}</h4>
            <p className="text-text-secondary text-sm mb-2">{target.role}</p>
            <p className="text-text-muted text-xs leading-relaxed">{target.description}</p>

            {selectedTarget === target.id && (
              <div className="mt-3 flex items-center gap-1.5 text-brand-400 text-xs font-semibold animate-fade-in">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                </svg>
                Selected
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="animate-fade-in">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-brand-300 to-brand-500 bg-clip-text text-transparent">
          Select a Target
        </h2>
        <p className="text-text-secondary mt-2 text-base">
          Choose a prominent figure for the misinformation scenario
        </p>
      </div>

      {renderGrid(politicians, '🏛️ Politicians')}
      {renderGrid(celebrities, '⭐ Celebrities & Public Figures')}
    </div>
  );
}
