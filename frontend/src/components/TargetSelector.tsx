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
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {items.map((target, i) => (
          <button
            id={`target-${target.id}`}
            key={target.id}
            onClick={() => onSelect(target.id)}
            className={`glass-card p-4 text-center cursor-pointer animate-slide-up group hover:scale-105 transition-transform duration-300 ${selectedTarget === target.id ? 'selected' : ''
              }`}
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className="relative mb-3">
              <div className={`w-full aspect-square rounded-2xl overflow-hidden bg-gradient-to-br ${categoryColors[target.category] || ''} border-2 ${selectedTarget === target.id ? 'border-brand-400 shadow-lg shadow-brand-400/30' : 'border-surface-600 group-hover:border-brand-400/50'
                } transition-all duration-300`}>
                <img
                  src={target.sample_image}
                  alt={target.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to icon if image fails to load
                    const icon = categoryIcons[target.category] || '👤';
                    e.currentTarget.style.display = 'none';
                    const parent = e.currentTarget.parentElement;
                    if (parent) {
                      parent.innerHTML = `<div class="w-full h-full flex items-center justify-center text-4xl">${icon}</div>`;
                    }
                  }}
                />
              </div>
              {selectedTarget === target.id && (
                <div className="absolute -top-2 -right-2 w-8 h-8 bg-brand-400 rounded-full flex items-center justify-center shadow-lg animate-fade-in">
                  <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
            <h4 className="text-text-primary font-semibold text-sm mb-1">{target.name}</h4>
            <p className="text-text-secondary text-xs">{target.role}</p>
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
