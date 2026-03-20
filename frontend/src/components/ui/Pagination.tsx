import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps { currentPage: number; totalPages: number; onPageChange: (page: number) => void }

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  const pages = Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1);
  return (
    <div className="flex items-center justify-center gap-1 mt-8">
      <button disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1)} className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50"><ChevronLeft className="w-5 h-5" /></button>
      {pages.map(p => (
        <button key={p} onClick={() => onPageChange(p)} className={`px-3 py-1.5 rounded-lg text-sm font-medium ${p === currentPage ? 'bg-wisestay-500 text-white' : 'hover:bg-gray-100'}`}>{p}</button>
      ))}
      <button disabled={currentPage >= totalPages} onClick={() => onPageChange(currentPage + 1)} className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50"><ChevronRight className="w-5 h-5" /></button>
    </div>
  );
}
