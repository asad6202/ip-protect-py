import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus, Settings, Edit, Trash2, Code } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import RuleSetForm from '../components/RuleSetForm'
import { useListRuleSets, useDeleteRuleSet } from '../api'
import { formatDateTime } from '@/lib-utils/format'

export default function RuleSetListPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingRuleSet, setEditingRuleSet] = useState<any>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: ruleSets, isLoading, error } = useListRuleSets()
  const deleteRuleSet = useDeleteRuleSet()

  const handleDelete = async (id: string) => {
    try {
      await deleteRuleSet.mutateAsync(id)
    } catch (error) {
      console.error('Error deleting rule set:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Rule Sets" 
          description="Manage quote generation rules"
          children={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Rule Set
            </Button>
          }
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </CardHeader>
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
          title="Rule Sets" 
          description="Manage quote generation rules"
          children={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Rule Set
            </Button>
          }
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Settings className="h-12 w-12" />}
              title="Error loading rule sets"
              description="There was an error loading the rule sets. Please try again."
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

  if (!ruleSets || ruleSets.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Rule Sets" 
          description="Manage quote generation rules"
          children={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Rule Set
            </Button>
          }
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Settings className="h-12 w-12" />}
              title="No rule sets yet"
              description="Create your first rule set to customize quote generation."
              action={{
                label: 'Create Rule Set',
                onClick: () => setShowForm(true)
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
        title="Rule Sets" 
        description="Manage quote generation rules"
        children={
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Rule Set
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {ruleSets.map((ruleSet) => (
          <Card key={ruleSet.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{ruleSet.name}</CardTitle>
                <div className="flex space-x-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setEditingRuleSet(ruleSet)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setDeleteConfirm(ruleSet.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <CardDescription>
                <div className="flex items-center space-x-2">
                  <Badge variant={ruleSet.is_active ? 'default' : 'outline'}>
                    {ruleSet.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <span>Priority: {ruleSet.priority}</span>
                </div>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground mb-4">
                Created {formatDateTime(ruleSet.created_at)}
              </div>
              <div className="flex space-x-2">
                <Button asChild variant="outline" size="sm" className="flex-1">
                  <Link to={`/rules/${ruleSet.id}`}>
                    <Code className="mr-2 h-4 w-4" />
                    Manage Rules
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Forms and Dialogs */}
      <RuleSetForm
        open={showForm}
        onOpenChange={setShowForm}
        onSuccess={() => setShowForm(false)}
      />

      <RuleSetForm
        open={!!editingRuleSet}
        onOpenChange={(open) => !open && setEditingRuleSet(null)}
        ruleSet={editingRuleSet}
        onSuccess={() => setEditingRuleSet(null)}
      />

      <ConfirmDialog
        open={!!deleteConfirm}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
        title="Delete Rule Set"
        description="Are you sure you want to delete this rule set? This action cannot be undone and will affect all associated rules."
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
