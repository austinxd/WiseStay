import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages = Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1);

  return (
    <div className="flex items-center justify-center gap-1 mt-12">
      <button
        disabled={currentPage <= 1}
        onClick={() => onPageChange(currentPage - 1)}
        className="p-2 rounded-lg text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100
                 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      {pages.map(p => (
        <button
          key={p}
          onClick={() => onPageChange(p)}
          className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors
                     ${p === currentPage
                       ? 'bg-neutral-900 text-white'
                       : 'text-neutral-600 hover:bg-neutral-100'}`}
        >
          {p}
        </button>
      ))}

      <button
        disabled={currentPage >= totalPages}
        onClick={() => onPageChange(currentPage + 1)}
        className="p-2 rounded-lg text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100
                 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
}
