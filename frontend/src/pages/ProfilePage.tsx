import { useAuthStore } from '@/stores/authStore';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export function ProfilePage() {
  const { user } = useAuthStore();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-heading font-bold">Profile</h1>
      <Card><CardContent>
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-wisestay-100 flex items-center justify-center text-2xl font-bold text-wisestay-600">{user?.first_name?.[0] || user?.email?.[0]}</div>
            <div><p className="text-lg font-semibold">{user?.first_name} {user?.last_name}</p><p className="text-sm text-gray-500">{user?.email}</p><Badge color="blue">{user?.role}</Badge></div>
          </div>
          {user?.phone && <div><p className="text-sm text-gray-500">Phone</p><p>{user.phone}</p></div>}
        </div>
      </CardContent></Card>
    </div>
  );
}
