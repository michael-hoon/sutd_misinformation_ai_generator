interface StepIndicatorProps {
  currentStep: number;
  steps: string[];
}

export default function StepIndicator({ currentStep, steps }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2 mb-10">
      {steps.map((label, i) => {
        const stepNum = i + 1;
        const isActive = stepNum === currentStep;
        const isComplete = stepNum < currentStep;

        return (
          <div key={i} className="flex items-center gap-2">
            {/* Step circle */}
            <div className="flex items-center gap-3">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300
                  ${isComplete
                    ? 'bg-brand-500 text-white shadow-[0_0_16px_oklch(0.55_0.22_280/0.4)]'
                    : isActive
                      ? 'bg-brand-500/20 text-brand-300 border-2 border-brand-400 shadow-[0_0_16px_oklch(0.55_0.22_280/0.3)]'
                      : 'bg-surface-700 text-text-muted border border-surface-600'
                  }
                `}
              >
                {isComplete ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  stepNum
                )}
              </div>
              <span
                className={`text-sm font-medium hidden sm:block transition-colors duration-300 ${
                  isActive ? 'text-brand-300' : isComplete ? 'text-text-secondary' : 'text-text-muted'
                }`}
              >
                {label}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                className={`w-12 h-0.5 transition-colors duration-300 ${
                  isComplete ? 'bg-brand-500' : 'bg-surface-600'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
