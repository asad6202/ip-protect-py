import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { Quote, CreateQuoteRequest, UpdateQuoteRequest, QuoteGenResponse, PaginatedResponse } from '@/lib/types'

// Generate quote from prompt
export function useGenerateQuote() {
  return useMutation({
    mutationFn: async (prompt: string): Promise<QuoteGenResponse> => {
      const response = await api.post('/api/v1/quote/generate', { prompt })
      return response.data
    },
  })
}

// Fetch all quotes
export function useListQuotes() {
  return useQuery({
    queryKey: ['quotes'],
    queryFn: async (): Promise<PaginatedResponse<Quote>> => {
      const response = await api.get('/api/v1/quotes')
      return response.data
    },
  })
}

// Fetch single quote
export function useGetQuote(id: string) {
  return useQuery({
    queryKey: ['quotes', id],
    queryFn: async (): Promise<Quote> => {
      const response = await api.get(`/api/v1/quotes/${id}`)
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
      const response = await api.post('/api/v1/quote', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })
}

// Update quote
export function useUpdateQuote() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateQuoteRequest }): Promise<Quote> => {
      const response = await api.patch(`/api/v1/quotes/${id}`, data)
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
      await api.delete(`/api/v1/quotes/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
    },
  })
}
