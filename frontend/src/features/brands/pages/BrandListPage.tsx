import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus, Building2, Edit, Trash2 } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import BrandForm from '../components/BrandForm'
import { useListBrands, useDeleteBrand } from '../api'
import { formatDateTime } from '@/lib/format'

export default function BrandListPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingBrand, setEditingBrand] = useState<any>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: brands, isLoading, error } = useListBrands()
  const deleteBrand = useDeleteBrand()

  const handleDelete = async (id: string) => {
    try {
      await deleteBrand.mutateAsync(id)
    } catch (error) {
      console.error('Error deleting brand:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Brands" 
          description="Manage product brands"
          children={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Brand
            </Button>
          }
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </CardHeader>
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
          title="Brands" 
          description="Manage product brands"
          children={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Brand
            </Button>
          }
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Building2 className="h-12 w-12" />}
              title="Error loading brands"
              description="There was an error loading the brands. Please try again."
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

  if (!brands || brands.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Brands" 
          description="Manage product brands"
          children={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Brand
            </Button>
          }
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Building2 className="h-12 w-12" />}
              title="No brands yet"
              description="Get started by creating your first brand."
              action={{
                label: 'Create Brand',
                onClick: () => setShowForm(true)
              }}
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Brands" 
        description="Manage product brands"
        children={
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Brand
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {brands.map((brand) => (
          <Card key={brand.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{brand.name}</CardTitle>
                <div className="flex space-x-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setEditingBrand(brand)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeleteConfirm(brand.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {brand.slug && (
                <CardDescription>
                  <Badge variant="outline">{brand.slug}</Badge>
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground">
                Created {formatDateTime(brand.created_at)}
              </div>
              <div className="mt-4">
                <Button asChild variant="outline" size="sm">
                  <Link to={`/brands/${brand.id}`}>
                    View Details
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Forms and Dialogs */}
      <BrandForm
        open={showForm}
        onOpenChange={setShowForm}
        onSuccess={() => setShowForm(false)}
      />

      <BrandForm
        open={!!editingBrand}
        onOpenChange={(open) => !open && setEditingBrand(null)}
        brand={editingBrand}
        onSuccess={() => setEditingBrand(null)}
      />

      <ConfirmDialog
        open={!!deleteConfirm}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
        title="Delete Brand"
        description="Are you sure you want to delete this brand? This action cannot be undone."
        confirmText="Delete"
        variant="destructive"
        onConfirm={() => {
          if (deleteConfirm) {
            handleDelete(deleteConfirm)
            setDeleteConfirm(null)
          }
        }}
      />
    </div>
  )
}
