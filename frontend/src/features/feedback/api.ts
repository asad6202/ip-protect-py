import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { Feedback, CreateFeedbackRequest } from '@/lib-utils/types'

// Fetch feedback for a quote
export function useGetFeedback(quoteId: string) {
  return useQuery({
    queryKey: ['feedback', quoteId],
    queryFn: async (): Promise<Feedback[]> => {
      const response = await api.get(`/v1/quote/${quoteId}/feedback`)
      return response.data
    },
    enabled: !!quoteId,
  })
}

// Create feedback
export function useCreateFeedback() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ quoteId, data }: { quoteId: string; data: CreateFeedbackRequest }): Promise<Feedback> => {
      const response = await api.post(`/v1/quote/${quoteId}/feedback`, data)
      return response.data
    },
    onSuccess: (_, { quoteId }) => {
      queryClient.invalidateQueries({ queryKey: ['feedback', quoteId] })
    },
  })
}
