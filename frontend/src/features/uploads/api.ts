import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { ProductUpload } from '@/lib/types'

// Fetch all uploads
export function useListUploads() {
  return useQuery({
    queryKey: ['uploads'],
    queryFn: async (): Promise<ProductUpload[]> => {
      const response = await api.get('/api/v1/uploads')
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
