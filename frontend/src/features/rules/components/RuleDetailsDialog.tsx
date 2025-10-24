import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Rule } from '@/lib-utils/types'
import { formatDateTime } from '@/lib-utils/format'
import { Eye, Trash2, Wand2 } from 'lucide-react'

interface RuleDetailsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  rule: Rule | null
  onDelete?: (ruleId: string) => void
}

export default function RuleDetailsDialog({ 
  open, 
  onOpenChange, 
  rule, 
  onDelete 
}: RuleDetailsDialogProps) {
  if (!rule) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Rule Details
          </DialogTitle>
          <DialogDescription>
            View detailed information about this rule
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 overflow-y-auto flex-1 pr-2 pb-4">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Name</label>
                  <p className="text-sm">{rule.name}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Status</label>
                  <div className="mt-1">
                    <Badge variant={rule.active ? 'default' : 'outline'}>
                      {rule.active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Scope</label>
                  <div className="mt-1">
                    <Badge variant="outline">
                      {rule.scope}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Priority</label>
                  <p className="text-sm">{rule.priority}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* NLP Command */}
          {rule.nlp_command && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Wand2 className="h-5 w-5" />
                  Original NLP Command
                </CardTitle>
                <CardDescription>
                  The natural language command used to create this rule
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                    "{rule.nlp_command}"
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Condition */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Rule Conditions</CardTitle>
              <CardDescription>
                What this rule applies to
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(rule.condition).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                    <span className="font-medium capitalize text-sm">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-sm text-gray-600">
                      {typeof value === 'object' && value !== null 
                        ? Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(', ')
                        : String(value)
                      }
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Rule Effect */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Rule Effect</CardTitle>
              <CardDescription>
                What this rule does when conditions are met
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(rule.actions).map(([key, value]) => {
                  let description = '';
                  if (key === 'boost_score') {
                    const multiplier = parseFloat(value as string);
                    if (multiplier > 1) {
                      description = `Increases preference by ${Math.round((multiplier - 1) * 100)}%`;
                    } else if (multiplier < 1) {
                      description = `Decreases preference by ${Math.round((1 - multiplier) * 100)}%`;
                    } else {
                      description = 'No preference change';
                    }
                  } else if (key === 'filter') {
                    description = value ? 'Filters out items that don\'t match' : 'No filtering applied';
                  } else if (key === 'penalty') {
                    const penalty = parseFloat(value as string);
                    description = `Applies ${Math.round(penalty * 100)}% penalty`;
                  } else {
                    description = `${key}: ${value}`;
                  }
                  
                  return (
                    <div key={key} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                      <span className="font-medium capitalize text-sm">
                        {key.replace(/_/g, ' ')}:
                      </span>
                      <span className="text-sm text-gray-600">
                        {description}
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>


          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Created</label>
                  <p className="text-sm">{formatDateTime(rule.created_at)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Updated</label>
                  <p className="text-sm">{formatDateTime(rule.updated_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4 border-t flex-shrink-0 bg-background">
          {onDelete && (
            <Button
              variant="destructive"
              onClick={() => {
                onDelete(rule.id)
                onOpenChange(false)
              }}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Rule
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
