import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Rule, CreateRuleRequest, UpdateRuleRequest } from '@/lib-utils/types'
import { useCreateRule, useUpdateRule } from '../api'

const ruleSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  active: z.boolean().default(true),
  scope: z.enum(['global', 'item']),
  priority: z.number().min(0).default(0),
  condition: z.string().min(1, 'Condition is required'),
  actions: z.string().min(1, 'Actions are required'),
})

type RuleFormData = z.infer<typeof ruleSchema>

interface RuleFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  ruleSetId: string
  rule?: Rule
  onSuccess?: () => void
}

const presetTemplates = {
  'prefer-axis': {
    name: 'Prefer Axis Brand',
    condition: JSON.stringify({ brand: 'Axis' }, null, 2),
    actions: JSON.stringify({ boost_score: 1.2 }, null, 2),
  },
  'avoid-ptz': {
    name: 'Avoid PTZ Cameras',
    condition: JSON.stringify({ type: 'ptz' }, null, 2),
    actions: JSON.stringify({ boost_score: 0.5 }, null, 2),
  },
  'hard-filter-ports': {
    name: 'Hard Filter: Switch Ports >= 24',
    condition: JSON.stringify({ switch_ports: { gte: 24 } }, null, 2),
    actions: JSON.stringify({ filter: true }, null, 2),
  },
  'budget-cap': {
    name: 'Budget Cap Per Item',
    condition: JSON.stringify({ price: { lte: 1000 } }, null, 2),
    actions: JSON.stringify({ boost_score: 1.1 }, null, 2),
  },
}

export default function RuleForm({ 
  open, 
  onOpenChange, 
  ruleSetId,
  rule, 
  onSuccess 
}: RuleFormProps) {
  const [jsonErrors, setJsonErrors] = useState<{condition?: string, actions?: string}>({})
  
  const createRule = useCreateRule()
  const updateRule = useUpdateRule()
  
  const isEditing = !!rule

  const form = useForm<RuleFormData>({
    resolver: zodResolver(ruleSchema),
    defaultValues: {
      name: rule?.name || '',
      active: rule?.active ?? true,
      scope: rule?.scope || 'global',
      priority: rule?.priority || 0,
      condition: rule?.condition ? JSON.stringify(rule.condition, null, 2) : '',
      actions: rule?.actions ? JSON.stringify(rule.actions, null, 2) : '',
    },
  })

  const validateJson = (value: string, field: 'condition' | 'actions') => {
    try {
      JSON.parse(value)
      setJsonErrors(prev => ({ ...prev, [field]: undefined }))
      return true
    } catch (error) {
      setJsonErrors(prev => ({ 
        ...prev, 
        [field]: `Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}` 
      }))
      return false
    }
  }

  const applyTemplate = (template: keyof typeof presetTemplates) => {
    const preset = presetTemplates[template]
    form.setValue('name', preset.name)
    form.setValue('condition', preset.condition)
    form.setValue('actions', preset.actions)
    validateJson(preset.condition, 'condition')
    validateJson(preset.actions, 'actions')
  }

  const onSubmit = async (data: RuleFormData) => {
    // Validate JSON
    const conditionValid = validateJson(data.condition, 'condition')
    const actionsValid = validateJson(data.actions, 'actions')
    
    if (!conditionValid || !actionsValid) {
      return
    }

    try {
      const ruleData = {
        ...data,
        rule_set_id: ruleSetId,
        condition: JSON.parse(data.condition),
        actions: JSON.parse(data.actions),
      }

      if (isEditing) {
        await updateRule.mutateAsync({
          id: rule.id,
          data: ruleData as UpdateRuleRequest,
        })
      } else {
        await createRule.mutateAsync(ruleData as CreateRuleRequest)
      }
      form.reset()
      setJsonErrors({})
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Error saving rule:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Rule' : 'Create Rule'}
          </DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the rule configuration below.'
              : 'Create a new rule to customize quote generation behavior.'
            }
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                {...form.register('name')}
                placeholder="Rule name"
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
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="scope">Scope</Label>
              <Select
                value={form.watch('scope')}
                onValueChange={(value) => form.setValue('scope', value as 'global' | 'item')}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="global">Global</SelectItem>
                  <SelectItem value="item">Item</SelectItem>
                </SelectContent>
              </Select>
              {form.formState.errors.scope && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.scope.message}
                </p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="active"
                {...form.register('active')}
                className="rounded border-input"
              />
              <Label htmlFor="active">Active</Label>
            </div>
          </div>

          {/* Preset Templates */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Quick Templates</CardTitle>
              <CardDescription>
                Apply common rule configurations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(presetTemplates).map(([key, template]) => (
                  <Button
                    key={key}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => applyTemplate(key as keyof typeof presetTemplates)}
                  >
                    {template.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Condition */}
          <div className="space-y-2">
            <Label htmlFor="condition">Condition (JSON) *</Label>
            <Textarea
              id="condition"
              {...form.register('condition')}
              placeholder='{"brand": "Axis", "price": {"lte": 1000}}'
              className="min-h-[120px] font-mono text-sm"
              onChange={(e) => {
                form.setValue('condition', e.target.value)
                validateJson(e.target.value, 'condition')
              }}
            />
            {jsonErrors.condition && (
              <p className="text-sm text-destructive">{jsonErrors.condition}</p>
            )}
            {form.formState.errors.condition && (
              <p className="text-sm text-destructive">
                {form.formState.errors.condition.message}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <Label htmlFor="actions">Actions (JSON) *</Label>
            <Textarea
              id="actions"
              {...form.register('actions')}
              placeholder='{"boost_score": 1.2, "filter": true}'
              className="min-h-[120px] font-mono text-sm"
              onChange={(e) => {
                form.setValue('actions', e.target.value)
                validateJson(e.target.value, 'actions')
              }}
            />
            {jsonErrors.actions && (
              <p className="text-sm text-destructive">{jsonErrors.actions}</p>
            )}
            {form.formState.errors.actions && (
              <p className="text-sm text-destructive">
                {form.formState.errors.actions.message}
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
              disabled={createRule.isPending || updateRule.isPending}
            >
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
