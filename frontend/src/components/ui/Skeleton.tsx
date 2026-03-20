export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-neutral-200 rounded ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="card animate-pulse">
      <div className="h-64 bg-neutral-200" />
      <div className="p-5 space-y-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="flex gap-4 pt-2">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
    </div>
  );
}
