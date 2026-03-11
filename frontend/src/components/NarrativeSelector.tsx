import type { Narrative } from '../api';

interface NarrativeSelectorProps {
  narratives: Narrative[];
  selectedNarrative: string | null;
  onSelect: (id: string) => void;
}

const categoryLabels: Record<string, string> = {
  financial_fraud: 'Financial Fraud',
  social_harm: 'Social Harm',
  political: 'Political',
  health: 'Health',
  public_safety: 'Public Safety',
};

const categoryBadgeColors: Record<string, string> = {
  financial_fraud: 'bg-amber-500/15 text-amber-400',
  social_harm: 'bg-red-500/15 text-red-400',
  political: 'bg-blue-500/15 text-blue-400',
  health: 'bg-green-500/15 text-green-400',
  public_safety: 'bg-orange-500/15 text-orange-400',
};

export default function NarrativeSelector({ narratives, selectedNarrative, onSelect }: NarrativeSelectorProps) {
  return (
    <div className="animate-fade-in">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-accent-400 to-accent-500 bg-clip-text text-transparent">
          Select a Narrative
        </h2>
        <p className="text-text-secondary mt-2 text-base">
          Choose a misinformation topic to generate
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {narratives.map((narrative, i) => (
          <button
            id={`narrative-${narrative.id}`}
            key={narrative.id}
            onClick={() => onSelect(narrative.id)}
            className={`glass-card p-5 text-left cursor-pointer animate-slide-up ${
              selectedNarrative === narrative.id ? 'selected' : ''
            }`}
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className="flex items-start justify-between mb-3">
              <span className="text-3xl">{narrative.icon}</span>
              <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full ${
                categoryBadgeColors[narrative.category] || 'bg-surface-600 text-text-muted'
              }`}>
                {categoryLabels[narrative.category] || narrative.category}
              </span>
            </div>

            <h4 className="text-text-primary font-semibold text-base mb-2">{narrative.title}</h4>
            <p className="text-text-muted text-xs leading-relaxed">{narrative.description}</p>

            {selectedNarrative === narrative.id && (
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
}
