import { useMutation, useQuery } from '@tanstack/react-query'
import api from '@/lib-utils/api'

interface ChatResponse {
  message: string
  updated_items?: any[]
  modifications?: any
}

interface ChatHistory {
  history: Array<{
    role: string
    content: string
    timestamp?: string
  }>
}

export function useModifyQuoteWithChat() {
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post<ChatResponse>(
        '/v1/chat/modify-quote',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      return response.data
    },
  })
}

export function useGetChatHistory(quoteId: string) {
  return useQuery({
    queryKey: ['chat-history', quoteId],
    queryFn: async () => {
      const response = await api.get<ChatHistory>(`/v1/chat/${quoteId}/history`)
      return response.data.history
    },
    enabled: !!quoteId,
  })
}
