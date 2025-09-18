import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { PromptRun } from '@/lib/types'

// Fetch all prompt runs
export function useListPromptRuns() {
  return useQuery({
    queryKey: ['prompt-runs'],
    queryFn: async (): Promise<PromptRun[]> => {
      const response = await api.get('/api/v1/prompt_runs')
      return response.data
    },
  })
}

// Fetch single prompt run
export function useGetPromptRun(id: string) {
  return useQuery({
    queryKey: ['prompt-runs', id],
    queryFn: async (): Promise<PromptRun> => {
      const response = await api.get(`/api/v1/prompt_runs/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}
