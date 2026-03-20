import type { ReactNode } from 'react';
import { Button } from './Button';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="text-center py-16">
      {icon && <div className="flex justify-center mb-4 text-neutral-400">{icon}</div>}
      <h3 className="text-lg font-semibold text-neutral-900 mb-2">{title}</h3>
      {description && <p className="text-neutral-500 mb-6">{description}</p>}
      {action && (
        <Button variant="secondary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
