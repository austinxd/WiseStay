const colors: Record<string, string> = {
  green: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
  blue: 'bg-sky-50 text-sky-700 ring-1 ring-sky-200',
  yellow: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  red: 'bg-rose-50 text-rose-700 ring-1 ring-rose-200',
  gray: 'bg-gray-50 text-gray-600 ring-1 ring-gray-200',
  purple: 'bg-violet-50 text-violet-700 ring-1 ring-violet-200',
  gold: 'bg-accent-50 text-accent-700 ring-1 ring-accent-200',
};

interface BadgeProps { children: React.ReactNode; color?: string; className?: string }

export function Badge({ children, color = 'gray', className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold tracking-wide ${colors[color] || colors.gray} ${className}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    active: { color: 'green', label: 'Active' },
    confirmed: { color: 'green', label: 'Confirmed' },
    checked_in: { color: 'blue', label: 'In Stay' },
    checked_out: { color: 'gray', label: 'Completed' },
    pending: { color: 'yellow', label: 'Pending' },
    cancelled: { color: 'red', label: 'Cancelled' },
    draft: { color: 'gray', label: 'Draft' },
    approved: { color: 'blue', label: 'Approved' },
    paid: { color: 'green', label: 'Paid' },
    failed: { color: 'red', label: 'Failed' },
    online: { color: 'green', label: 'Online' },
    offline: { color: 'red', label: 'Offline' },
    escalated: { color: 'yellow', label: 'Escalated' },
  };
  const { color, label } = map[status] || { color: 'gray', label: status };
  return <Badge color={color}>{label}</Badge>;
}
