import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Edit, Trash2, Upload, Package, File, Trash2 as TrashIcon } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import BrandForm from '../components/BrandForm'
import UploadDialog from '../../uploads/components/UploadDialog'
import { useGetBrand, useDeleteBrand } from '../api'
import { useListUploads, useDeleteUpload } from '../../uploads/api'
import { formatDateTime } from '@/lib-utils/format'

export default function BrandDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [showEditForm, setShowEditForm] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [showUploadDialog, setShowUploadDialog] = useState(false)
  const [deleteUploadConfirm, setDeleteUploadConfirm] = useState<string | null>(null)

  const { data: brand, isLoading, error } = useGetBrand(id!)
  const deleteBrand = useDeleteBrand()
  const { data: uploads, isLoading: uploadsLoading } = useListUploads(id)
  const deleteUpload = useDeleteUpload()

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

  const handleDeleteUpload = async (uploadId: string) => {
    try {
      await deleteUpload.mutateAsync(uploadId)
      setDeleteUploadConfirm(null)
    } catch (error) {
      console.error('Error deleting upload:', error)
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
            <Button 
              variant="outline" 
              className="w-full"
              onClick={() => setShowUploadDialog(true)}
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload Products
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Uploads */}
      <Card>
        <CardHeader>
          <CardTitle>Product Uploads</CardTitle>
          <CardDescription>
            Files uploaded for this brand
          </CardDescription>
        </CardHeader>
        <CardContent>
          {uploadsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-muted rounded w-1/2"></div>
                </div>
              ))}
            </div>
          ) : uploads && uploads.length > 0 ? (
            <div className="space-y-3">
              {uploads.map((upload) => (
                <div key={upload.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <File className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{upload.original_name}</p>
                      <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                        <span>{formatDateTime(upload.created_at)}</span>
                        {upload.row_count && (
                          <>
                            <span>•</span>
                            <span>{upload.row_count} rows</span>
                          </>
                        )}
                        <Badge 
                          variant={upload.status === 'processed' ? 'default' : 
                                  upload.status === 'processing' ? 'secondary' : 'destructive'}
                        >
                          {upload.status}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteUploadConfirm(upload.id)}
                    >
                      <TrashIcon className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <File className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-4">
                No uploads yet. Upload a CSV file to get started.
              </p>
              <Button 
                variant="outline" 
                onClick={() => setShowUploadDialog(true)}
              >
                <Upload className="mr-2 h-4 w-4" />
                Upload Products
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Forms and Dialogs */}
      <BrandForm
        open={showEditForm}
        onOpenChange={setShowEditForm}
        brand={brand}
        onSuccess={() => setShowEditForm(false)}
      />

      <UploadDialog
        open={showUploadDialog}
        onOpenChange={setShowUploadDialog}
        onSuccess={() => setShowUploadDialog(false)}
        defaultBrandId={brand?.id}
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

      <ConfirmDialog
        open={!!deleteUploadConfirm}
        onOpenChange={(open) => !open && setDeleteUploadConfirm(null)}
        title="Delete Upload"
        description="Are you sure you want to delete this upload? This action cannot be undone."
        confirmText="Delete"
        variant="destructive"
        onConfirm={() => {
          if (deleteUploadConfirm) {
            handleDeleteUpload(deleteUploadConfirm)
          }
        }}
      />
    </div>
  )
}
