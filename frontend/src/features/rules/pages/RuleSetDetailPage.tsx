import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Plus, Edit, Trash2, Code, Settings } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import RuleForm from '../components/RuleForm'
import { useGetRuleSet, useListRules, useDeleteRule } from '../api'
import { formatDateTime } from '@/lib-utils/format'

export default function RuleSetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [showRuleForm, setShowRuleForm] = useState(false)
  const [editingRule, setEditingRule] = useState<any>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: ruleSet, isLoading, error } = useGetRuleSet(id!)
  const { data: rules, isLoading: rulesLoading } = useListRules(id!)
  const deleteRule = useDeleteRule()

  const handleDelete = async (ruleId: string) => {
    if (!ruleSet) return
    try {
      await deleteRule.mutateAsync({ id: ruleId, ruleSetId: ruleSet.id })
    } catch (error) {
      console.error('Error deleting rule:', error)
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

  if (error || !ruleSet) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Rule Set Not Found" 
          description=""
          showBackButton
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Settings className="h-12 w-12" />}
              title="Rule set not found"
              description="The rule set you're looking for doesn't exist or has been deleted."
              action={{
                label: 'Back to Rule Sets',
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
        title={ruleSet.name}
        description={`Priority: ${ruleSet.priority} • ${ruleSet.is_active ? 'Active' : 'Inactive'}`}
        showBackButton
        children={
          <Button onClick={() => setShowRuleForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Rule
          </Button>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Rule Set Info */}
        <Card>
          <CardHeader>
            <CardTitle>Rule Set Information</CardTitle>
            <CardDescription>
              Basic information about this rule set
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">Name</label>
              <p className="text-lg font-semibold">{ruleSet.name}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Status</label>
              <p className="text-lg">
                <Badge variant={ruleSet.is_active ? 'default' : 'outline'}>
                  {ruleSet.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Priority</label>
              <p className="text-lg font-semibold">{ruleSet.priority}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Created</label>
              <p className="text-sm">{formatDateTime(ruleSet.created_at)}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
              <p className="text-sm">{formatDateTime(ruleSet.updated_at)}</p>
            </div>
          </CardContent>
        </Card>

        {/* Rules Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Rules Summary</CardTitle>
            <CardDescription>
              Overview of rules in this set
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="text-2xl font-bold">
                {rules?.length || 0} rules
              </div>
              <div className="text-sm text-muted-foreground">
                {rules?.filter(r => r.active).length || 0} active
              </div>
              <div className="text-sm text-muted-foreground">
                {rules?.filter(r => r.scope === 'global').length || 0} global scope
              </div>
              <div className="text-sm text-muted-foreground">
                {rules?.filter(r => r.scope === 'item').length || 0} item scope
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Rules List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Rules</CardTitle>
              <CardDescription>
                Manage individual rules in this set
              </CardDescription>
            </div>
            <Button onClick={() => setShowRuleForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {rulesLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-16 bg-muted rounded"></div>
                </div>
              ))}
            </div>
          ) : !rules || rules.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Code className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No rules in this set yet.</p>
              <p className="text-sm">Add your first rule to get started.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Scope</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {rule.scope}
                      </Badge>
                    </TableCell>
                    <TableCell>{rule.priority}</TableCell>
                    <TableCell>
                      <Badge variant={rule.active ? 'default' : 'outline'}>
                        {rule.active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditingRule(rule)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleteConfirm(rule.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Forms and Dialogs */}
      <RuleForm
        open={showRuleForm}
        onOpenChange={setShowRuleForm}
        ruleSetId={ruleSet.id}
        onSuccess={() => setShowRuleForm(false)}
      />

      <RuleForm
        open={!!editingRule}
        onOpenChange={(open) => !open && setEditingRule(null)}
        ruleSetId={ruleSet.id}
        rule={editingRule}
        onSuccess={() => setEditingRule(null)}
      />

      <ConfirmDialog
        open={!!deleteConfirm}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
        title="Delete Rule"
        description="Are you sure you want to delete this rule? This action cannot be undone."
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
