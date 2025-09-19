import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Plus, Upload, File, Trash2, CheckCircle, XCircle, Clock } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import UploadDialog from '../components/UploadDialog'
import { useListUploads, useDeleteUpload, useUploadProgress } from '../api'
import { formatRelativeTime } from '@/lib-utils/format'

const statusConfig = {
  uploaded: { icon: Clock, color: 'bg-yellow-100 text-yellow-800', label: 'Uploaded' },
  queued: { icon: Clock, color: 'bg-yellow-100 text-yellow-800', label: 'Queued' },
  processing: { icon: Clock, color: 'bg-blue-100 text-blue-800', label: 'Processing' },
  processed: { icon: CheckCircle, color: 'bg-green-100 text-green-800', label: 'Processed' },
  completed: { icon: CheckCircle, color: 'bg-green-100 text-green-800', label: 'Completed' },
  failed: { icon: XCircle, color: 'bg-red-100 text-red-800', label: 'Failed' },
}

// Individual Upload Card with Progress Tracking
function UploadCard({ upload, onDelete }: { upload: any; onDelete: (id: string) => void }) {
  const statusInfo = statusConfig[upload.status] || statusConfig.uploaded
  const StatusIcon = statusInfo.icon
  
  // Use progress polling for processing uploads
  const isProcessing = upload.status === 'queued' || upload.status === 'processing'
  const { data: progressData } = useUploadProgress(upload.id, isProcessing)
  
  // Use progress data if available, otherwise fall back to upload data
  const currentData = progressData || upload
  
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <File className="h-8 w-8 text-muted-foreground" />
            <div className="flex-1">
              <h3 className="font-semibold">{currentData.filename || upload.original_name}</h3>
              <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                <span>
                  {currentData.total_rows ? `${(currentData.total_rows ?? 0).toLocaleString()} rows` : 'Unknown rows'}
                </span>
                <span>•</span>
                <span>{formatRelativeTime(currentData.created_at || upload.created_at)}</span>
                {currentData.completed_at && (
                  <>
                    <span>•</span>
                    <span>Completed {formatRelativeTime(currentData.completed_at)}</span>
                  </>
                )}
              </div>
              
              {/* Progress Bar for Processing Uploads */}
              {isProcessing && progressData && (
                <div className="mt-3 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>Processing...</span>
                    <span>
                      {(progressData.processed_rows ?? 0).toLocaleString()} / {(progressData.total_rows ?? 0).toLocaleString()} 
                      ({progressData.progress_percent ?? 0}%)
                    </span>
                  </div>
                  <Progress value={progressData.progress_percent ?? 0} className="h-2" />
                  {(progressData.error_count ?? 0) > 0 && (
                    <div className="text-xs text-amber-600">
                      {progressData.error_count} errors encountered
                    </div>
                  )}
                </div>
              )}
              
              {currentData.message && (
                <p className="text-sm text-destructive mt-1">{currentData.message}</p>
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
              onClick={() => onDelete(upload.id)}
              disabled={isProcessing}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
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
          return <UploadCard key={upload.id} upload={upload} onDelete={setDeleteConfirm} />
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
