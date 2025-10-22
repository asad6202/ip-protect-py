import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { QuoteItemFeedback, CreateItemFeedbackRequest } from '@/lib-utils/types'

// Create item feedback
export function useCreateItemFeedback() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ itemId, data }: { itemId: string; data: CreateItemFeedbackRequest }): Promise<QuoteItemFeedback> => {
      const response = await api.post(`/v1/quote-items/${itemId}/feedback`, data)
      return response.data
    },
    onSuccess: (_, { itemId }) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['item-feedback', itemId] })
      queryClient.invalidateQueries({ queryKey: ['quote-item-feedback'] })
    },
  })
}

// Get feedback for a specific item
export function useGetItemFeedback(itemId: string) {
  return useQuery({
    queryKey: ['item-feedback', itemId],
    queryFn: async (): Promise<QuoteItemFeedback[]> => {
      const response = await api.get(`/v1/quote-items/${itemId}/feedback`)
      return response.data
    },
    enabled: !!itemId,
  })
}

// Get all item feedback for a quote
export function useGetQuoteItemFeedback(quoteId: string) {
  return useQuery({
    queryKey: ['quote-item-feedback', quoteId],
    queryFn: async (): Promise<QuoteItemFeedback[]> => {
      const response = await api.get(`/v1/quotes/${quoteId}/item-feedback`)
      return response.data
    },
    enabled: !!quoteId,
  })
}

// Get item feedback analytics
export function useGetItemFeedbackAnalytics() {
  return useQuery({
    queryKey: ['item-feedback-analytics'],
    queryFn: async () => {
      const response = await api.get('/v1/item-feedback/analytics')
      return response.data
    },
  })
}
