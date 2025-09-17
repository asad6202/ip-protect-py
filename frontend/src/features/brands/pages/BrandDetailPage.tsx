import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Edit, Trash2, Upload, Package } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import BrandForm from '../components/BrandForm'
import { useGetBrand, useDeleteBrand } from '../api'
import { formatDateTime } from '@/lib/format'

export default function BrandDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [showEditForm, setShowEditForm] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  const { data: brand, isLoading, error } = useGetBrand(id!)
  const deleteBrand = useDeleteBrand()

  const handleDelete = async () => {
    if (!brand) return
    try {
      await deleteBrand.mutateAsync(brand.id)
      // Navigate back to brands list
      window.history.back()
    } catch (error) {
      console.error('Error deleting brand:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Loading..." 
          description=""
          showBackButton
        />
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="animate-pulse">
            <CardHeader>
              <div className="h-6 bg-muted rounded w-1/2"></div>
              <div className="h-4 bg-muted rounded w-1/3"></div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="h-4 bg-muted rounded"></div>
                <div className="h-4 bg-muted rounded w-2/3"></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (error || !brand) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Brand Not Found" 
          description=""
          showBackButton
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Package className="h-12 w-12" />}
              title="Brand not found"
              description="The brand you're looking for doesn't exist or has been deleted."
              action={{
                label: 'Back to Brands',
                onClick: () => window.history.back()
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
        title={brand.name}
        description={brand.slug ? `Slug: ${brand.slug}` : 'Brand details'}
        showBackButton
        children={
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => setShowEditForm(true)}
            >
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
            <Button
              variant="destructive"
              onClick={() => setDeleteConfirm(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Brand Info */}
        <Card>
          <CardHeader>
            <CardTitle>Brand Information</CardTitle>
            <CardDescription>
              Basic information about this brand
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">Name</label>
              <p className="text-lg font-semibold">{brand.name}</p>
            </div>
            {brand.slug && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">Slug</label>
                <p className="text-lg">
                  <Badge variant="outline">{brand.slug}</Badge>
                </p>
              </div>
            )}
            <div>
              <label className="text-sm font-medium text-muted-foreground">Created</label>
              <p className="text-sm">{formatDateTime(brand.created_at)}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
              <p className="text-sm">{formatDateTime(brand.updated_at)}</p>
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks for this brand
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button asChild className="w-full">
              <Link to={`/products?brand_id=${brand.id}`}>
                <Package className="mr-2 h-4 w-4" />
                View Products
              </Link>
            </Button>
            <Button asChild variant="outline" className="w-full">
              <Link to={`/uploads?brand_id=${brand.id}`}>
                <Upload className="mr-2 h-4 w-4" />
                Upload Products
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Uploads */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Uploads</CardTitle>
          <CardDescription>
            Latest product uploads for this brand
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            No uploads yet. Upload a CSV file to get started.
          </div>
        </CardContent>
      </Card>

      {/* Forms and Dialogs */}
      <BrandForm
        open={showEditForm}
        onOpenChange={setShowEditForm}
        brand={brand}
        onSuccess={() => setShowEditForm(false)}
      />

      <ConfirmDialog
        open={deleteConfirm}
        onOpenChange={setDeleteConfirm}
        title="Delete Brand"
        description="Are you sure you want to delete this brand? This action cannot be undone and will affect all associated products."
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  )
}
