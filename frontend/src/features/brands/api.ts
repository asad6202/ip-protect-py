import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { Brand, CreateBrandRequest, UpdateBrandRequest } from '@/lib-utils/types'

// Fetch all brands
export function useListBrands() {
  return useQuery({
    queryKey: ['brands'],
    queryFn: async (): Promise<Brand[]> => {
      const response = await api.get('/api/v1/brands')
      return response.data
    },
  })
}

// Fetch single brand
export function useGetBrand(id: string) {
  return useQuery({
    queryKey: ['brands', id],
    queryFn: async (): Promise<Brand> => {
      const response = await api.get(`/api/v1/brands/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

// Create brand
export function useCreateBrand() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreateBrandRequest): Promise<Brand> => {
      const response = await api.post('/api/v1/brands', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
    },
  })
}

// Update brand
export function useUpdateBrand() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateBrandRequest }): Promise<Brand> => {
      const response = await api.patch(`/api/v1/brands/${id}`, data)
      return response.data
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
      queryClient.invalidateQueries({ queryKey: ['brands', id] })
    },
  })
}

// Delete brand
export function useDeleteBrand() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/api/v1/brands/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
    },
  })
}