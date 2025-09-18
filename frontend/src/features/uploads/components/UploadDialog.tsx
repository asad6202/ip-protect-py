import { useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Upload, File, X, AlertCircle } from 'lucide-react'
import { useUploadFile } from '../api'
import { useListBrands } from '../../brands/api'

const uploadSchema = z.object({
  brand_id: z.string().min(1, 'Brand selection is required'),
})

type UploadFormData = z.infer<typeof uploadSchema>

interface UploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  defaultBrandId?: string
}

export default function UploadDialog({ 
  open, 
  onOpenChange, 
  onSuccess,
  defaultBrandId
}: UploadDialogProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  
  const uploadFile = useUploadFile()
  const { data: brands } = useListBrands()

  const form = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
  })

  // Set default brand ID when dialog opens
  useEffect(() => {
    if (open && defaultBrandId) {
      form.setValue('brand_id', defaultBrandId)
    }
  }, [open, defaultBrandId, form])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0])
        setUploadError(null)
      }
    },
    onDropRejected: (fileRejections) => {
      const error = fileRejections[0]?.errors[0]
      if (error) {
        setUploadError(error.message)
      }
    },
  })

  const onSubmit = async (data: UploadFormData) => {
    if (!file) {
      setUploadError('Please select a file to upload')
      return
    }

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (data.brand_id) {
        formData.append('brand_id', data.brand_id)
      }

      await uploadFile.mutateAsync(formData)
      
      // Clear file and form after successful upload
      setFile(null)
      form.reset()
      setUploadError(null)
      
      // Call success callback and close dialog
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Error uploading file:', error)
      setUploadError('Failed to upload file. Please try again.')
    }
  }

  const removeFile = () => {
    setFile(null)
    setUploadError(null)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl w-full max-w-[90vw]">
        <DialogHeader>
          <DialogTitle>Upload Products</DialogTitle>
          <DialogDescription>
            Upload a CSV or Excel file containing product data. The file must have the following required columns: SKU, description, price, currency, and family. Optional columns include form_factor, outdoor, poe, poe_plus, ir_range_m, resolution_mp, vandal_ik10, nvr_channels, switch_ports, is_accessory, and accessory_type.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {/* File Upload */}
          <div className="space-y-2">
            <Label>File</Label>
            {!file ? (
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? 'border-primary bg-primary/5'
                    : 'border-muted-foreground/25 hover:border-primary/50'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">
                  {isDragActive
                    ? 'Drop the file here...'
                    : 'Drag & drop a CSV file here, or click to select'
                  }
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  CSV, XLS, XLSX files accepted
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/50 gap-3">
                <div className="flex items-center space-x-3 min-w-0 flex-1">
                  <File className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium break-all">
                      {file.name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </div>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={removeFile}
                  className="flex-shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}
            {uploadError && (
              <div className="flex items-center space-x-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span>{uploadError}</span>
              </div>
            )}
          </div>

          {/* Brand Selection - Only show if no default brand ID */}
          {!defaultBrandId && (
            <div className="space-y-2">
              <Label htmlFor="brand_id">Brand *</Label>
              <Select
                value={form.watch('brand_id')}
                onValueChange={(value) => form.setValue('brand_id', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a brand" />
                </SelectTrigger>
                <SelectContent>
                  {brands?.map((brand) => (
                    <SelectItem key={brand.id} value={brand.id}>
                      {brand.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.formState.errors.brand_id && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.brand_id.message}
                </p>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!file || (!defaultBrandId && !form.watch('brand_id')) || uploadFile.isPending}
            >
              {uploadFile.isPending ? 'Uploading...' : 'Upload'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
