const colors: Record<string, string> = {
  green: 'bg-green-100 text-green-800',
  blue: 'bg-blue-100 text-blue-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
  gray: 'bg-gray-100 text-gray-800',
  purple: 'bg-purple-100 text-purple-800',
};

interface BadgeProps { children: React.ReactNode; color?: keyof typeof colors; className?: string }

export function Badge({ children, color = 'gray', className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[color] || colors.gray} ${className}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    active: { color: 'green', label: 'Active' },
    confirmed: { color: 'green', label: 'Confirmed' },
    checked_in: { color: 'blue', label: 'Checked In' },
    checked_out: { color: 'gray', label: 'Checked Out' },
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
