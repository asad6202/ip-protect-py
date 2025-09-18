import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Brand, CreateBrandRequest, UpdateBrandRequest } from '@/lib/types'
import { useCreateBrand, useUpdateBrand } from '../api'

const brandSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  slug: z.string().optional(),
})

type BrandFormData = z.infer<typeof brandSchema>

interface BrandFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  brand?: Brand
  onSuccess?: () => void
}

export default function BrandForm({ 
  open, 
  onOpenChange, 
  brand, 
  onSuccess 
}: BrandFormProps) {
  const createBrand = useCreateBrand()
  const updateBrand = useUpdateBrand()
  
  const isEditing = !!brand

  const form = useForm<BrandFormData>({
    resolver: zodResolver(brandSchema),
    defaultValues: {
      name: brand?.name || '',
      slug: brand?.slug || '',
    },
  })

  const onSubmit = async (data: BrandFormData) => {
    try {
      if (isEditing) {
        await updateBrand.mutateAsync({
          id: brand.id,
          data: data as UpdateBrandRequest,
        })
      } else {
        await createBrand.mutateAsync(data as CreateBrandRequest)
      }
      form.reset()
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Error saving brand:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Brand' : 'Create Brand'}
          </DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the brand information below.'
              : 'Add a new brand to the system.'
            }
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              {...form.register('name')}
              placeholder="Brand name"
            />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="slug">Slug</Label>
            <Input
              id="slug"
              {...form.register('slug')}
              placeholder="brand-slug (optional)"
            />
            {form.formState.errors.slug && (
              <p className="text-sm text-destructive">
                {form.formState.errors.slug.message}
              </p>
            )}
          </div>

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
              disabled={createBrand.isPending || updateBrand.isPending}
            >
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
