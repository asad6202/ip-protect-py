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
import { RuleSet, CreateRuleSetRequest, UpdateRuleSetRequest } from '@/lib-utils/types'
import { useCreateRuleSet, useUpdateRuleSet } from '../api'

const ruleSetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  is_active: z.boolean().default(true),
  priority: z.number().min(0).default(0),
})

type RuleSetFormData = z.infer<typeof ruleSetSchema>

interface RuleSetFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  ruleSet?: RuleSet
  onSuccess?: () => void
}

export default function RuleSetForm({ 
  open, 
  onOpenChange, 
  ruleSet, 
  onSuccess 
}: RuleSetFormProps) {
  const createRuleSet = useCreateRuleSet()
  const updateRuleSet = useUpdateRuleSet()
  
  const isEditing = !!ruleSet

  const form = useForm<RuleSetFormData>({
    resolver: zodResolver(ruleSetSchema),
    defaultValues: {
      name: ruleSet?.name || '',
      is_active: ruleSet?.is_active ?? true,
      priority: ruleSet?.priority || 0,
    },
  })

  const onSubmit = async (data: RuleSetFormData) => {
    try {
      if (isEditing) {
        await updateRuleSet.mutateAsync({
          id: ruleSet.id,
          data: data as UpdateRuleSetRequest,
        })
      } else {
        await createRuleSet.mutateAsync(data as CreateRuleSetRequest)
      }
      form.reset()
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Error saving rule set:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Rule Set' : 'Create Rule Set'}
          </DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the rule set information below.'
              : 'Create a new rule set to organize your quote generation rules.'
            }
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              {...form.register('name')}
              placeholder="Rule set name"
            />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="priority">Priority</Label>
            <Input
              id="priority"
              type="number"
              min="0"
              {...form.register('priority', { valueAsNumber: true })}
              placeholder="0"
            />
            {form.formState.errors.priority && (
              <p className="text-sm text-destructive">
                {form.formState.errors.priority.message}
              </p>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="is_active"
              {...form.register('is_active')}
              className="rounded border-input"
            />
            <Label htmlFor="is_active">Active</Label>
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
              disabled={createRuleSet.isPending || updateRuleSet.isPending}
            >
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
