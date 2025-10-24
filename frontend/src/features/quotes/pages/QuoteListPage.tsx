import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Plus, Search, Eye, Trash2, Copy, X } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import { useListQuotes, useDeleteQuote } from '../api'
import { formatCurrency, formatRelativeTime } from '@/lib-utils/format'

const statusConfig = {
  draft: { color: 'bg-gray-100 text-gray-800', label: 'Draft' },
  sent: { color: 'bg-blue-100 text-blue-800', label: 'Sent' },
  accepted: { color: 'bg-green-100 text-green-800', label: 'Accepted' },
  rejected: { color: 'bg-red-100 text-red-800', label: 'Rejected' },
  expired: { color: 'bg-yellow-100 text-yellow-800', label: 'Expired' },
}

export default function QuoteListPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: quotesData, isLoading, error, refetch } = useListQuotes()
  const deleteQuote = useDeleteQuote()

  // Refetch quotes when component mounts (when user navigates back)
  useEffect(() => {
    refetch()
  }, [refetch])

  const handleDelete = async (id: string) => {
    try {
      await deleteQuote.mutateAsync(id)
    } catch (error) {
      console.error('Error deleting quote:', error)
    }
  }

  const quotes = quotesData?.items || []
  const trimmedSearch = search.trim()
  
  const filteredQuotes = quotes.filter(quote => {
    const matchesSearch = !trimmedSearch || 
      quote.title?.toLowerCase().includes(trimmedSearch.toLowerCase()) ||
      quote.prompt.toLowerCase().includes(trimmedSearch.toLowerCase())
    const matchesStatus = !statusFilter || statusFilter === 'all' || quote.status === statusFilter
    return matchesSearch && matchesStatus
  })

  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        {/* Fixed Header */}
        <div className="flex-shrink-0 space-y-6">
          <PageHeader 
            title="Quotes" 
            description="Manage your quotes"
            children={
              <Button asChild className="btn-protect-outline">
                <Link to="/quotes/new">
                  <Plus className="mr-2 h-4 w-4" />
                  New Quote
                </Link>
              </Button>
            }
          />
        </div>

        {/* Loading State Container with Responsive Height */}
        <div className="flex-1 min-h-0">
          <div className="h-full max-h-[60vh] sm:max-h-[65vh] md:max-h-[70vh] lg:max-h-[75vh] xl:max-h-[80vh] overflow-y-auto">
            <div className="space-y-4 pb-6">
              {[...Array(5)].map((_, i) => (
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
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex flex-col">
        {/* Fixed Header */}
        <div className="flex-shrink-0 space-y-6">
          <PageHeader 
            title="Quotes" 
            description="Manage your quotes"
            children={
              <Button asChild className="btn-protect-outline">
                <Link to="/quotes/new">
                  <Plus className="mr-2 h-4 w-4" />
                  New Quote
                </Link>
              </Button>
            }
          />
        </div>

        {/* Error State Container with Responsive Height */}
        <div className="flex-1 min-h-0">
          <div className="h-full max-h-[60vh] sm:max-h-[65vh] md:max-h-[70vh] lg:max-h-[75vh] xl:max-h-[80vh] overflow-y-auto">
            <Card>
              <CardContent className="py-12">
                <EmptyState
                  icon={<Search className="h-12 w-12" />}
                  title="Error loading quotes"
                  description="There was an error loading the quotes. Please try again."
                  action={{
                    label: 'Retry',
                    onClick: () => window.location.reload()
                  }}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  if (!quotes || quotes.length === 0) {
    return (
      <div className="h-full flex flex-col">
        {/* Fixed Header */}
        <div className="flex-shrink-0 space-y-6">
          <PageHeader 
            title="Quotes" 
            description="Manage your quotes"
            children={
              <Button asChild className="btn-protect-outline">
                <Link to="/quotes/new">
                  <Plus className="mr-2 h-4 w-4" />
                  New Quote
                </Link>
              </Button>
            }
          />
        </div>

        {/* Empty State Container with Responsive Height */}
        <div className="flex-1 min-h-0">
          <div className="h-full max-h-[60vh] sm:max-h-[65vh] md:max-h-[70vh] lg:max-h-[75vh] xl:max-h-[80vh] overflow-y-auto">
            <Card>
              <CardContent className="py-12">
                <EmptyState
                  icon={<Search className="h-12 w-12" />}
                  title="No quotes yet"
                  description="Create your first quote to get started."
                  action={{
                    label: 'Create Quote',
                    onClick: () => window.location.href = '/quotes/new'
                  }}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Fixed Header */}
      <div className="flex-shrink-0 space-y-6">
        <PageHeader 
          title="Quotes" 
          description="Manage your quotes"
          children={
            <Button asChild>
              <Link to="/quotes/new">
                <Plus className="mr-2 h-4 w-4" />
                New Quote
              </Link>
            </Button>
          }
        />

        {/* Filters */}
        <Card className="mb-8">
          <CardContent className="p-4">
            <div className="flex flex-col space-y-4 lg:flex-row lg:space-y-0 lg:space-x-4">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search quotes..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>

              {/* Status Filter */}
              <div className="w-full lg:w-48">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All statuses</SelectItem>
                    {Object.entries(statusConfig).map(([status, config]) => (
                      <SelectItem key={status} value={status}>
                        {config.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

            {/* Clear Filters */}
            {(trimmedSearch || statusFilter) && (
                <Button size="sm" className="btn-protect-outline" onClick={() => {
                  setSearch('')
                  setStatusFilter('')
                }}>
                  <X className="mr-2 h-4 w-4" />
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quotes List Container with Responsive Height */}
      <div className="flex-1 min-h-0 mt-5">
        <div className="h-full max-h-[60vh] sm:max-h-[65vh] md:max-h-[70vh] lg:max-h-[75vh] xl:max-h-[80vh] overflow-y-auto">
          <div className="space-y-4 pb-6">
        {filteredQuotes.map((quote) => {
          const statusInfo = statusConfig[quote.status]
          const total = quote.total_amount || 0
          const currency = quote.currency || 'USD'

          return (
            <Card key={quote.id}>
              <CardContent className="p-6 hover:bg-muted transition-colors duration-200">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-4">
                      <div>
                        <h3 className="font-semibold text-lg">
                          {quote.title || 'Untitled Quote'}
                        </h3>
                        <p className="text-muted-foreground text-sm mt-1">
                          {quote.prompt.length > 100 
                            ? `${quote.prompt.substring(0, 100)}...`
                            : quote.prompt
                          }
                        </p>
                        <div className="flex items-center space-x-4 mt-2 text-sm text-muted-foreground">
                          <span>{formatRelativeTime(quote.created_at)}</span>
                          <span>•</span>
                          <span>
                            {(() => {
                              const extractedCount = quote.extracted_intent?.items?.length || 0
                              const itemsCount = quote.items?.length || 0
                              const finalCount = extractedCount || itemsCount || 0
                              return `${finalCount} items`
                            })()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="text-lg font-semibold">
                        {formatCurrency(total, currency)}
                      </p>
                      <Badge className={statusInfo.color}>
                        {statusInfo.label}
                      </Badge>
                    </div>
                    <div className="flex space-x-2">
                      <Button asChild variant="ghost" size="icon">
                        <Link to={`/quotes/${quote.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                      <Button variant="ghost" size="icon">
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeleteConfirm(quote.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
          </div>
        </div>
      </div>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteConfirm}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
        title="Delete Quote"
        description="Are you sure you want to delete this quote? This action cannot be undone."
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
