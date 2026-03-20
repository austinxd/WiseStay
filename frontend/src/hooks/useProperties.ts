import { useQuery } from '@tanstack/react-query';
import { propertyService } from '@/services/propertyService';

export function useProperties(params?: Record<string, any>) {
  return useQuery({ queryKey: ['properties', params], queryFn: () => propertyService.list(params) });
}

export function useProperty(slug: string) {
  return useQuery({ queryKey: ['property', slug], queryFn: () => propertyService.get(slug), enabled: !!slug });
}
