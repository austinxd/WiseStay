import type { ReactNode } from 'react';
import { Button } from './Button';

interface EmptyStateProps { icon?: ReactNode; title: string; description?: string; action?: { label: string; onClick: () => void } }

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      {icon && <div className="flex justify-center mb-4 text-gray-400">{icon}</div>}
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      {action && <div className="mt-6"><Button onClick={action.onClick}>{action.label}</Button></div>}
    </div>
  );
}
