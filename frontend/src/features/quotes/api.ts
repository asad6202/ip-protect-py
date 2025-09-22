import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { Quote, CreateQuoteRequest, UpdateQuoteRequest, QuoteGenResponse, PaginatedResponse } from '@/lib-utils/types'

// Generate quote from prompt
export function useGenerateQuote() {
  return useMutation({
    mutationFn: async (prompt: string): Promise<QuoteGenResponse> => {
      const response = await api.post('/v1/quote/generate', { prompt })
      return response.data
    },
  })
}

// Fetch all quotes
export function useListQuotes() {
  return useQuery({
    queryKey: ['quotes'],
    queryFn: async (): Promise<PaginatedResponse<Quote>> => {
      const response = await api.get('/v1/quotes')
      return response.data
    },
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    staleTime: 0, // Always consider stale
  })
}

// Fetch single quote
export function useGetQuote(id: string) {
  return useQuery({
    queryKey: ['quotes', id],
    queryFn: async (): Promise<Quote> => {
      const response = await api.get(`/v1/quote/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

// Create quote
export function useCreateQuote() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreateQuoteRequest): Promise<Quote> => {
      const response = await api.post('/v1/quote', data)
      return response.data
    },
    onSuccess: (newQuote) => {
      // Invalidate and refetch quotes list
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      
      // Force refetch the quotes list
      queryClient.refetchQueries({ queryKey: ['quotes'] })
      
      // Also add the new quote to the cache optimistically
      queryClient.setQueryData(['quotes', newQuote.id], newQuote)
    },
  })
}

// Update quote
export function useUpdateQuote() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateQuoteRequest }): Promise<Quote> => {
      const response = await api.patch(`/v1/quote/${id}`, data)
      return response.data
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      queryClient.invalidateQueries({ queryKey: ['quotes', id] })
    },
  })
}

// Delete quote
export function useDeleteQuote() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/v1/quote/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })
}
