import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Package, Search, Filter, Eye } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import { useListProducts, useProductFamilies } from '../api'
import { useListBrands } from '../../brands/api'
import { formatCurrency } from '@/lib/format'

export default function ProductListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [brandFilter, setBrandFilter] = useState(searchParams.get('brand_id') || '')
  const [familyFilter, setFamilyFilter] = useState(searchParams.get('family') || '')
  const [accessoryFilter, setAccessoryFilter] = useState(searchParams.get('is_accessory') || '')
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'))

  const filters = {
    search: search || undefined,
    brand_id: brandFilter || undefined,
    family: familyFilter || undefined,
    is_accessory: accessoryFilter ? accessoryFilter === 'true' : undefined,
    page,
    page_size: 20,
  }

  const { data: productsData, isLoading, error } = useListProducts(filters)
  const { data: brands } = useListBrands()
  const { data: families } = useProductFamilies()

  const handleSearch = () => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (brandFilter) params.set('brand_id', brandFilter)
    if (familyFilter) params.set('family', familyFilter)
    if (accessoryFilter) params.set('is_accessory', accessoryFilter)
    if (page > 1) params.set('page', page.toString())
    
    setSearchParams(params)
  }

  const clearFilters = () => {
    setSearch('')
    setBrandFilter('')
    setFamilyFilter('')
    setAccessoryFilter('')
    setPage(1)
    setSearchParams({})
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Products" 
          description="Browse and search products"
        />
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-48"></div>
                    <div className="h-3 bg-muted rounded w-32"></div>
                  </div>
                  <div className="h-6 bg-muted rounded w-20"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Products" 
          description="Browse and search products"
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Package className="h-12 w-12" />}
              title="Error loading products"
              description="There was an error loading the products. Please try again."
              action={{
                label: 'Retry',
                onClick: () => window.location.reload()
              }}
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  const products = productsData?.items || []
  const totalPages = productsData?.pages || 1

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Products" 
        description="Browse and search products"
      />

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Filter className="mr-2 h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search products..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Brand</label>
              <Select value={brandFilter} onValueChange={setBrandFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All brands" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All brands</SelectItem>
                  {brands?.map((brand) => (
                    <SelectItem key={brand.id} value={brand.id}>
                      {brand.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Family</label>
              <Select value={familyFilter} onValueChange={setFamilyFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All families" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All families</SelectItem>
                  {families?.map((family) => (
                    <SelectItem key={family} value={family}>
                      {family}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Type</label>
              <Select value={accessoryFilter} onValueChange={setAccessoryFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All types</SelectItem>
                  <SelectItem value="false">Products</SelectItem>
                  <SelectItem value="true">Accessories</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-between mt-4">
            <Button variant="outline" onClick={clearFilters}>
              Clear Filters
            </Button>
            <Button onClick={handleSearch}>
              Apply Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {products.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Package className="h-12 w-12" />}
              title="No products found"
              description="Try adjusting your search criteria or upload some products."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {products.map((product) => (
            <Card key={product.id}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-4">
                      <div>
                        <h3 className="font-semibold text-lg">{product.sku}</h3>
                        <p className="text-muted-foreground">{product.description}</p>
                        <div className="flex items-center space-x-2 mt-2">
                          <Badge variant="outline">{product.family}</Badge>
                          {product.is_accessory && (
                            <Badge variant="secondary">Accessory</Badge>
                          )}
                          {product.outdoor && (
                            <Badge variant="outline">Outdoor</Badge>
                          )}
                          {product.poe && (
                            <Badge variant="outline">PoE</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold">
                      {formatCurrency(product.price, product.currency)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {product.status}
                    </p>
                    <Button asChild variant="outline" size="sm" className="mt-2">
                      <Link to={`/products/${product.id}`}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                      </Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center space-x-2">
              <Button
                variant="outline"
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="flex items-center px-4 text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
