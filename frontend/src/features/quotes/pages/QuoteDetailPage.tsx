import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { 
  Edit, 
  Trash2, 
  Copy, 
  Download, 
  Send,
  MessageSquare,
  Star
} from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import { useGetQuote, useDeleteQuote, useUpdateQuote } from '../api'
import { useGetFeedback } from '../../feedback/api'
import FeedbackForm from '../../feedback/components/FeedbackForm'
import { formatCurrency, formatDateTime } from '@/lib/format'

const statusConfig = {
  draft: { color: 'bg-gray-100 text-gray-800', label: 'Draft' },
  sent: { color: 'bg-blue-100 text-blue-800', label: 'Sent' },
  accepted: { color: 'bg-green-100 text-green-800', label: 'Accepted' },
  rejected: { color: 'bg-red-100 text-red-800', label: 'Rejected' },
  expired: { color: 'bg-yellow-100 text-yellow-800', label: 'Expired' },
}

export default function QuoteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [isEditingNotes, setIsEditingNotes] = useState(false)
  const [notes, setNotes] = useState('')

  const { data: quote, isLoading, error } = useGetQuote(id!)
  const { data: feedback, isLoading: feedbackLoading } = useGetFeedback(id!)
  const deleteQuote = useDeleteQuote()
  const updateQuote = useUpdateQuote()
  const [showFeedbackForm, setShowFeedbackForm] = useState(false)

  const handleDelete = async () => {
    if (!quote) return
    try {
      await deleteQuote.mutateAsync(quote.id)
      // Navigate back to quotes list
      window.history.back()
    } catch (error) {
      console.error('Error deleting quote:', error)
    }
  }

  const handleUpdateNotes = async () => {
    if (!quote) return
    try {
      await updateQuote.mutateAsync({
        id: quote.id,
        data: { notes }
      })
      setIsEditingNotes(false)
    } catch (error) {
      console.error('Error updating notes:', error)
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

  if (error || !quote) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Quote Not Found" 
          description=""
          showBackButton
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<MessageSquare className="h-12 w-12" />}
              title="Quote not found"
              description="The quote you're looking for doesn't exist or has been deleted."
              action={{
                label: 'Back to Quotes',
                onClick: () => window.history.back()
              }}
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  const statusInfo = statusConfig[quote.status]
  const total = quote.total_amount || 0
  const currency = quote.currency || 'USD'

  return (
    <div className="space-y-6">
      <PageHeader 
        title={quote.title || 'Untitled Quote'}
        description={`Created ${formatDateTime(quote.created_at)}`}
        showBackButton
        children={
          <div className="flex space-x-2">
            <Button className="btn-protect-outline">
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </Button>
            <Button className="btn-protect-outline">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button className="btn-protect-outline">
              <Send className="mr-2 h-4 w-4" />
              Send
            </Button>
            <Button
              variant="destructive"
              onClick={() => setDeleteConfirm(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Quote Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Quote Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Quote Information</CardTitle>
                <Badge className={statusInfo.color}>
                  {statusInfo.label}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Original Prompt</label>
                <p className="text-sm mt-1 p-3 bg-muted rounded-md">
                  {quote.prompt}
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Total Amount</label>
                  <p className="text-2xl font-bold">
                    {formatCurrency(total, currency)}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Items</label>
                  <p className="text-lg font-semibold">
                    {quote.items?.length || 0} items
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Items Table */}
          <Card>
            <CardHeader>
              <CardTitle>Quote Items</CardTitle>
              <CardDescription>
                Products and services included in this quote
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!quote.items || quote.items.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No items in this quote
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>SKU</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Unit Price</TableHead>
                      <TableHead className="text-right">Subtotal</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {quote.items.map((item, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-mono text-sm">
                          {item.sku}
                        </TableCell>
                        <TableCell>{item.description}</TableCell>
                        <TableCell className="text-right">
                          {item.quantity}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(item.unit_price, item.currency)}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(item.subtotal, item.currency)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Feedback Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Feedback
                  </CardTitle>
                  <CardDescription>
                    Share your thoughts to help us improve
                  </CardDescription>
                </div>
                <Button 
                  onClick={() => setShowFeedbackForm(true)}
                  className="flex items-center gap-2 btn-protect-outline"
                >
                  <MessageSquare className="h-4 w-4" />
                  Add Feedback
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {feedbackLoading ? (
                <div className="space-y-4">
                  {[1, 2].map((i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-muted rounded w-1/4 mb-2"></div>
                      <div className="h-3 bg-muted rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-muted rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : feedback && feedback.length > 0 ? (
                <div className="space-y-4">
                  {feedback.map((fb) => (
                    <div key={fb.id} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          {fb.rating && (
                            <div className="flex items-center gap-1">
                              {[1, 2, 3, 4, 5].map((star) => (
                                <Star
                                  key={star}
                                  className={`h-4 w-4 ${
                                    star <= fb.rating! 
                                      ? 'text-yellow-400 fill-current' 
                                      : 'text-gray-300'
                                  }`}
                                />
                              ))}
                            </div>
                          )}
                          <span className="text-sm text-muted-foreground">
                            {formatDateTime(fb.created_at)}
                          </span>
                        </div>
                      </div>
                      
                      {fb.comment && (
                        <p className="text-sm mb-3">{fb.comment}</p>
                      )}
                      
                      {fb.labels && (
                        <div className="space-y-2">
                          {(fb.labels as any).issues && (
                            <div>
                              <h4 className="text-sm font-medium text-red-600">Issues:</h4>
                              <p className="text-sm text-muted-foreground">{(fb.labels as any).issues}</p>
                            </div>
                          )}
                          {(fb.labels as any).suggestions && (
                            <div>
                              <h4 className="text-sm font-medium text-blue-600">Suggestions:</h4>
                              <p className="text-sm text-muted-foreground">{(fb.labels as any).suggestions}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6">
                  <MessageSquare className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No feedback yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Be the first to provide feedback on this quote
                  </p>
                  <Button onClick={() => setShowFeedbackForm(true)} className="btn-protect-outline">
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Add Feedback
                  </Button>
                </div>
              )}

              {/* Feedback Form */}
              {showFeedbackForm && (
                <div className="mt-6">
                  <FeedbackForm
                    quoteId={id!}
                    onSuccess={() => setShowFeedbackForm(false)}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Notes */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Notes</CardTitle>
                <Button
                  size="sm"
                  className="btn-protect-outline"
                  onClick={() => {
                    if (isEditingNotes) {
                      handleUpdateNotes()
                    } else {
                      setNotes(quote.notes || '')
                      setIsEditingNotes(true)
                    }
                  }}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  {isEditingNotes ? 'Save' : 'Edit'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isEditingNotes ? (
                <div className="space-y-4">
                  <Textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add notes about this quote..."
                    className="min-h-[100px]"
                  />
                  <div className="flex justify-end space-x-2">
                    <Button
                      className="btn-protect-outline"
                      onClick={() => {
                        setIsEditingNotes(false)
                        setNotes('')
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {quote.notes || 'No notes added to this quote.'}
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status Update */}
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Current Status</span>
                <Badge className={statusInfo.color}>
                  {statusInfo.label}
                </Badge>
              </div>
              <Select
                value={quote.status}
                onValueChange={async (newStatus) => {
                  try {
                    await updateQuote.mutateAsync({
                      id: quote.id,
                      data: { status: newStatus }
                    })
                  } catch (error) {
                    console.error('Error updating status:', error)
                  }
                }}
                disabled={updateQuote.isPending}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(statusConfig).map(([status, config]) => (
                    <SelectItem key={status} value={status}>
                      <div className="flex items-center">
                        <div className={`w-2 h-2 rounded-full mr-2 ${config.color.split(' ')[0]}`}></div>
                        {config.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button className="w-full btn-protect-outline">
                <Send className="mr-2 h-4 w-4" />
                Send Quote
              </Button>
              <Button className="w-full btn-protect-outline">
                <Download className="mr-2 h-4 w-4" />
                Export PDF
              </Button>
              <Button className="w-full btn-protect-outline">
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </Button>
            </CardContent>
          </Card>

          {/* Feedback */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Star className="mr-2 h-5 w-5" />
                Feedback
              </CardTitle>
              <CardDescription>
                Customer feedback and ratings
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-4 text-muted-foreground">
                <Star className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No feedback yet</p>
              </div>
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDateTime(quote.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Updated</span>
                <span>{formatDateTime(quote.updated_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Currency</span>
                <span>{currency}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>


      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteConfirm}
        onOpenChange={setDeleteConfirm}
        title="Delete Quote"
        description="Are you sure you want to delete this quote? This action cannot be undone."
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  )
}
