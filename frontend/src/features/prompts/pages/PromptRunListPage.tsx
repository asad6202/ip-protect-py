import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Search, FileText, Eye, Clock, CheckCircle } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import { useListPromptRuns } from '../api'
import { formatDateTime, formatRelativeTime } from '@/lib-utils/format'

export default function PromptRunListPage() {
  const [search, setSearch] = useState('')

  const { data: promptRuns, isLoading, error } = useListPromptRuns()

  const filteredRuns = promptRuns?.filter(run => 
    !search || 
    run.prompt.toLowerCase().includes(search.toLowerCase())
  ) || []

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Prompt Runs" 
          description="Audit trail of quote generation prompts"
        />
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-3 bg-muted rounded w-1/2"></div>
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
          title="Prompt Runs" 
          description="Audit trail of quote generation prompts"
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<FileText className="h-12 w-12" />}
              title="Error loading prompt runs"
              description="There was an error loading the prompt runs. Please try again."
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

  if (!promptRuns || promptRuns.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Prompt Runs" 
          description="Audit trail of quote generation prompts"
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<FileText className="h-12 w-12" />}
              title="No prompt runs yet"
              description="Prompt runs will appear here as quotes are generated."
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Prompt Runs" 
        description="Audit trail of quote generation prompts"
      />

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Search className="mr-2 h-5 w-5" />
            Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search prompt runs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Prompt Runs List */}
      <div className="space-y-4">
        {filteredRuns.map((run) => (
          <Card key={run.id}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-4">
                    <FileText className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <h3 className="font-semibold text-lg">
                        {run.prompt.length > 80 
                          ? `${run.prompt.substring(0, 80)}...`
                          : run.prompt
                        }
                      </h3>
                      <div className="flex items-center space-x-4 mt-2 text-sm text-muted-foreground">
                        <span className="flex items-center">
                          <Clock className="mr-1 h-4 w-4" />
                          {formatRelativeTime(run.created_at)}
                        </span>
                        {run.result_quote_id && (
                          <span className="flex items-center text-green-600">
                            <CheckCircle className="mr-1 h-4 w-4" />
                            Quote Generated
                          </span>
                        )}
                        {run.extracted_intent && (
                          <Badge variant="outline">Intent Extracted</Badge>
                        )}
                        {run.rules_applied && (
                          <Badge variant="outline">Rules Applied</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  {run.result_quote_id && (
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/quotes/${run.result_quote_id}`}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Quote
                      </Link>
                    </Button>
                  )}
                  <div className="text-right text-sm text-muted-foreground">
                    {formatDateTime(run.created_at)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredRuns.length === 0 && search && (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Search className="h-12 w-12" />}
              title="No results found"
              description="Try adjusting your search criteria."
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
