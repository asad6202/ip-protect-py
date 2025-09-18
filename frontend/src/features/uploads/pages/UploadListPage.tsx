import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Plus, Upload, File, Trash2, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import UploadDialog from '../components/UploadDialog'
import { useListUploads, useDeleteUpload } from '../api'
import { formatDateTime, formatRelativeTime } from '@/lib/format'

const statusConfig = {
  uploaded: { icon: Clock, color: 'bg-yellow-100 text-yellow-800', label: 'Uploaded' },
  processing: { icon: Clock, color: 'bg-blue-100 text-blue-800', label: 'Processing' },
  processed: { icon: CheckCircle, color: 'bg-green-100 text-green-800', label: 'Processed' },
  failed: { icon: XCircle, color: 'bg-red-100 text-red-800', label: 'Failed' },
}

export default function UploadListPage() {
  const [showUploadDialog, setShowUploadDialog] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: uploads, isLoading, error } = useListUploads()
  const deleteUpload = useDeleteUpload()

  const handleDelete = async (id: string) => {
    try {
      await deleteUpload.mutateAsync(id)
    } catch (error) {
      console.error('Error deleting upload:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Uploads" 
          description="Manage product uploads"
          children={
            <Button onClick={() => setShowUploadDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Upload File
            </Button>
          }
        />
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
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
          title="Uploads" 
          description="Manage product uploads"
          children={
            <Button onClick={() => setShowUploadDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Upload File
            </Button>
          }
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Upload className="h-12 w-12" />}
              title="Error loading uploads"
              description="There was an error loading the uploads. Please try again."
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

  if (!uploads || uploads.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Uploads" 
          description="Manage product uploads"
          children={
            <Button onClick={() => setShowUploadDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Upload File
            </Button>
          }
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Upload className="h-12 w-12" />}
              title="No uploads yet"
              description="Upload a CSV file to get started with product management."
              action={{
                label: 'Upload File',
                onClick: () => setShowUploadDialog(true)
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
        title="Uploads" 
        description="Manage product uploads"
        children={
          <Button onClick={() => setShowUploadDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Upload File
          </Button>
        }
      />

      <div className="space-y-4">
        {uploads.map((upload) => {
          const statusInfo = statusConfig[upload.status]
          const StatusIcon = statusInfo.icon

          return (
            <Card key={upload.id}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <File className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <h3 className="font-semibold">{upload.original_name}</h3>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <span>
                          {upload.row_count ? `${upload.row_count.toLocaleString()} rows` : 'Unknown rows'}
                        </span>
                        <span>•</span>
                        <span>{formatRelativeTime(upload.created_at)}</span>
                        {upload.processed_at && (
                          <>
                            <span>•</span>
                            <span>Processed {formatRelativeTime(upload.processed_at)}</span>
                          </>
                        )}
                      </div>
                      {upload.message && (
                        <p className="text-sm text-destructive mt-1">{upload.message}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <Badge className={statusInfo.color}>
                      <StatusIcon className="mr-1 h-3 w-3" />
                      {statusInfo.label}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteConfirm(upload.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Upload Dialog */}
      <UploadDialog
        open={showUploadDialog}
        onOpenChange={setShowUploadDialog}
        onSuccess={() => setShowUploadDialog(false)}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteConfirm}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
        title="Delete Upload"
        description="Are you sure you want to delete this upload? This action cannot be undone."
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
