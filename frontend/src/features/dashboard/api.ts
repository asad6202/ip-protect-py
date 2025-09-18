import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib-utils/api'

export interface DashboardStats {
  brands: number
  products: number
  quotes: number
  uploads: number
}

export interface RecentQuote {
  id: string
  title: string
  total_amount: number
  currency: string
  status: string
  created_at: string
  updated_at: string
}

export interface RecentUpload {
  id: string
  brand_id: string | null
  original_name: string
  row_count: number | null
  status: string
  created_at: string
}

// Hook to fetch dashboard statistics
export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async (): Promise<DashboardStats> => {
      const response = await api.get('/api/v1/dashboard/stats')
      return response.data
    },
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    staleTime: 30000, // Consider fresh for 30 seconds
  })
}

// Hook to fetch recent quotes
export function useRecentQuotes(limit: number = 5) {
  return useQuery({
    queryKey: ['dashboard', 'recent-quotes', limit],
    queryFn: async (): Promise<RecentQuote[]> => {
      const response = await api.get(`/api/v1/dashboard/recent-quotes?limit=${limit}`)
      return response.data
    },
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    staleTime: 60000, // Consider fresh for 1 minute
  })
}

// Hook to fetch recent uploads
export function useRecentUploads(limit: number = 5) {
  return useQuery({
    queryKey: ['dashboard', 'recent-uploads', limit],
    queryFn: async (): Promise<RecentUpload[]> => {
      const response = await api.get(`/api/v1/dashboard/recent-uploads?limit=${limit}`)
      return response.data
    },
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    staleTime: 60000, // Consider fresh for 1 minute
  })
}