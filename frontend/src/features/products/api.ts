import { useQuery } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { Product, ProductFilters, PaginatedResponse } from '@/lib-utils/types'

// Fetch all products with filters
export function useListProducts(filters: ProductFilters = {}) {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: async (): Promise<PaginatedResponse<Product>> => {
      const params = new URLSearchParams()
      
      if (filters.brand_id) params.append('brand_id', filters.brand_id)
      if (filters.search) params.append('search', filters.search)
      if (filters.family) params.append('family', filters.family)
      if (filters.is_accessory !== undefined) params.append('is_accessory', filters.is_accessory.toString())
      if (filters.page) params.append('page', filters.page.toString())
      if (filters.page_size) params.append('page_size', filters.page_size.toString())

      const response = await api.get(`/api/v1/products?${params.toString()}`)
      return response.data
    },
  })
}

// Fetch single product
export function useGetProduct(id: string) {
  return useQuery({
    queryKey: ['products', id],
    queryFn: async (): Promise<Product> => {
      const response = await api.get(`/api/v1/products/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

// Fetch product families
export function useProductFamilies() {
  return useQuery({
    queryKey: ['product-families'],
    queryFn: async (): Promise<string[]> => {
      const response = await api.get('/api/v1/products/families')
      return response.data
    },
  })
}
