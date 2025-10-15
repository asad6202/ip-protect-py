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
  MessageSquare
} from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import ConfirmDialog from '@/components/common/ConfirmDialog'
import { useGetQuote, useDeleteQuote, useUpdateQuote } from '../api'
import { useGetQuoteItemFeedback } from '../api-item-feedback'
import { formatCurrency, formatDateTime } from '@/lib-utils/format'
import ItemFeedbackDialog from '../components/ItemFeedbackDialog'
import ItemFeedbackDisplay from '../components/ItemFeedbackDisplay'
import QuoteWidget from '../components/QuoteWidget'
import QuoteChatInterface from '../components/QuoteChatInterface'

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

  const { data: quote, isLoading, error, refetch } = useGetQuote(id!)
  const { data: itemFeedback = [] } = useGetQuoteItemFeedback(id!)
  const deleteQuote = useDeleteQuote()
  const updateQuote = useUpdateQuote()

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

      {/* Quote Widget */}
      <QuoteWidget quote={quote} onSendQuote={() => {
        console.log('Send quote clicked')
      }} />

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
                      <TableHead className="text-center">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {quote.items.map((item, index) => {
                      const isFeedbackLearning = item.metadata?.is_feedback_learning
                      return (
                        <TableRow 
                          key={index}
                          className={isFeedbackLearning ? 'bg-green-50 border-green-200' : ''}
                        >
                          <TableCell className="font-mono text-sm">
                            <div>
                              {item.sku}
                              {/* Show feedback learning indicator */}
                              {isFeedbackLearning && item.metadata?.replacement_sku && (
                                <div className="text-xs text-blue-600 mt-1 flex items-center gap-1">
                                  <span>🧠</span>
                                  <span>Learned: <span className="font-mono">{item.metadata.replacement_sku}</span></span>
                                </div>
                              )}
                            </div>
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
                          <TableCell className="text-center">
                            <ItemFeedbackDialog 
                              item={item} 
                              originalItem={(() => {
                                // If this item was manually replaced, show the original "Product not found" item for feedback
                                const hasReplacement = item.metadata?.is_manual_replacement || 
                                                     item.metadata?.feedback_corrected || 
                                                     item.metadata?.replacement_sku;
                                
                                console.log('QuoteDetailPage - Item SKU:', item.sku, 'Has replacement:', hasReplacement, 'Metadata:', item.metadata);
                                
                                // If this item was replaced, show the original "Product not found" item for feedback
                                if (hasReplacement && item.metadata?.original_sku) {
                                  console.log('QuoteDetailPage - Showing original "Product not found" item for feedback:', item.metadata.original_sku);
                                  return {
                                    sku: item.metadata.original_sku, // Use original SKU from metadata
                                    description: `Product not found: ${item.metadata.original_sku}`,
                                    quantity: item.quantity,
                                    unit_price: 0, // Original was not found, so price was 0
                                    currency: item.currency,
                                    subtotal: 0,
                                    product_id: null,
                                    metadata: {}
                                  };
                                }
                                return undefined;
                              })()}
                              trigger={
                                <Button variant="outline" size="sm" className="gap-1">
                                  <MessageSquare className="h-3 w-3" />
                                  Feedback
                                </Button>
                              }
                            />
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Item Feedback Summary */}
          {itemFeedback.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Item Feedback Summary</CardTitle>
                <CardDescription>
                  Feedback provided for individual items in this quote
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {quote.items?.map((item) => {
                  const itemFeedbackData = itemFeedback.filter(fb => fb.quote_item_id === item.id)
                  if (itemFeedbackData.length === 0) return null
                  
                  return (
                    <div key={item.id || item.sku}>
                      <h4 className="font-medium text-sm text-gray-700 mb-2">
                        {item.sku} - {item.description}
                      </h4>
                      <ItemFeedbackDisplay 
                        feedback={itemFeedbackData} 
                        itemId={item.id || item.sku}
                      />
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          )}

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

          {/* Chat Interface for Quote Modifications */}
          <QuoteChatInterface 
            quoteId={id!} 
            onQuoteUpdated={() => refetch()}
          />
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
