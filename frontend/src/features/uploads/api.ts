import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { ProductUpload } from '@/lib-utils/types'

// Fetch all uploads
export function useListUploads(brandId?: string) {
  return useQuery({
    queryKey: ['uploads', brandId],
    queryFn: async (): Promise<ProductUpload[]> => {
      const params = brandId ? `?brand_id=${brandId}` : ''
      const response = await api.get(`/api/v1/uploads${params}`)
      return response.data
    },
  })
}

// Fetch single upload
export function useGetUpload(id: string) {
  return useQuery({
    queryKey: ['uploads', id],
    queryFn: async (): Promise<ProductUpload> => {
      const response = await api.get(`/api/v1/uploads/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

// Upload file
export function useUploadFile() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (formData: FormData): Promise<ProductUpload> => {
      const response = await api.post('/api/v1/uploads', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploads'] })
    },
  })
}

// Progress tracking hook with polling
export function useUploadProgress(uploadId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['upload-progress', uploadId],
    queryFn: async () => {
      const response = await api.get(`/api/v1/uploads/${uploadId}/progress`)
      return response.data
    },
    enabled: enabled && !!uploadId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if still processing, stop when completed
      const data = query.state.data
      return data?.is_processing ? 2000 : false
    },
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  })
}

// Delete upload
export function useDeleteUpload() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/api/v1/uploads/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploads'] })
    },
  })
}
