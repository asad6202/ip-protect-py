import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { MessageSquare, ThumbsUp, ThumbsDown, AlertCircle, DollarSign, Hash, Package } from 'lucide-react'
import { useCreateItemFeedback } from '../api-item-feedback'
import { CreateItemFeedbackRequest, QuoteItem } from '@/lib-utils/types'

const feedbackSchema = z.object({
  feedback_type: z.enum(['correct', 'incorrect', 'missing', 'wrong_quantity', 'wrong_price', 'wrong_specs']),
  comment: z.string().optional(),
  suggested_sku: z.string().optional(),
  suggested_quantity: z.number().min(1).optional(),
  suggested_price: z.number().min(0).optional(),
})

type FeedbackFormData = z.infer<typeof feedbackSchema>

interface ItemFeedbackDialogProps {
  item: QuoteItem
  trigger?: React.ReactNode
  onFeedbackChange?: (itemId: string, feedback: any) => void
  originalItem?: QuoteItem // The original product being replaced (if this is a replacement)
}

const feedbackTypeOptions = [
  { value: 'correct', label: 'Correct', icon: ThumbsUp, color: 'text-green-600' },
  { value: 'incorrect', label: 'Incorrect Product', icon: ThumbsDown, color: 'text-red-600' },
  { value: 'missing', label: 'Missing Product', icon: AlertCircle, color: 'text-orange-600' },
  { value: 'wrong_quantity', label: 'Wrong Quantity', icon: Hash, color: 'text-blue-600' },
  { value: 'wrong_price', label: 'Wrong Price', icon: DollarSign, color: 'text-purple-600' },
  { value: 'wrong_specs', label: 'Wrong Specifications', icon: Package, color: 'text-gray-600' },
]

export default function ItemFeedbackDialog({ item, trigger, onFeedbackChange, originalItem }: ItemFeedbackDialogProps) {
  const [open, setOpen] = useState(false)
  const createFeedback = useCreateItemFeedback()

  // Use original item for feedback context, fallback to current item
  const feedbackItem = originalItem || item
  
  console.log('ItemFeedbackDialog - item:', item.sku, 'originalItem:', originalItem?.sku, 'feedbackItem:', feedbackItem.sku)
  
  // Load existing feedback from item metadata
  const existingFeedback = feedbackItem.metadata?.item_feedback || null

  const form = useForm<FeedbackFormData>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      feedback_type: existingFeedback?.feedback_type || 'correct',
      comment: existingFeedback?.comment || '',
      suggested_sku: existingFeedback?.suggested_sku || '',
      suggested_quantity: existingFeedback?.suggested_quantity || undefined,
      suggested_price: existingFeedback?.suggested_price || undefined,
    },
  })

  const selectedFeedbackType = form.watch('feedback_type')
  const selectedOption = feedbackTypeOptions.find(opt => opt.value === selectedFeedbackType)

  const onSubmit = async (data: FeedbackFormData) => {
    try {
      if (feedbackItem.id) {
        // Quote is saved, submit feedback to database
        await createFeedback.mutateAsync({
          itemId: feedbackItem.id,
          data: data as CreateItemFeedbackRequest
        })
      } else {
        // Quote not saved yet, store feedback in item metadata
        if (onFeedbackChange) {
          onFeedbackChange(feedbackItem.sku, data)
        }
      }
      setOpen(false)
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  const defaultTrigger = (
    <Button variant="outline" size="sm" className="gap-2">
      <MessageSquare className="h-4 w-4" />
      Feedback
    </Button>
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Item Feedback
          </DialogTitle>
          <DialogDescription>
            Help us improve by providing feedback on this specific item: <strong>{feedbackItem.sku}</strong>
            {originalItem && originalItem.sku !== item.sku && (
              <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-amber-800 text-sm">
                📝 This is feedback for the original product that was replaced. The current item shown below is the replacement.
              </div>
            )}
            {!feedbackItem.id && (
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-blue-800 text-sm">
                💡 Feedback will be saved with the quote when you create it.
              </div>
            )}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Item Details */}
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-medium text-sm text-gray-700 mb-2">Original Product (for feedback)</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">SKU:</span> {feedbackItem.sku}
              </div>
              <div>
                <span className="text-gray-500">Quantity:</span> {feedbackItem.quantity}
              </div>
              <div>
                <span className="text-gray-500">Price:</span> ${feedbackItem.unit_price}
              </div>
              <div>
                <span className="text-gray-500">Total:</span> ${feedbackItem.subtotal}
              </div>
            </div>
            <div className="mt-2">
              <span className="text-gray-500">Description:</span> {feedbackItem.description}
            </div>
          </div>

          {/* Current Item Details (if different from original) */}
          {originalItem && originalItem.sku !== item.sku && (
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="font-medium text-sm text-blue-800 mb-2">Current Replacement Item</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">SKU:</span> {item.sku}
                </div>
                <div>
                  <span className="text-gray-500">Quantity:</span> {item.quantity}
                </div>
                <div>
                  <span className="text-gray-500">Price:</span> ${item.unit_price}
                </div>
                <div>
                  <span className="text-gray-500">Total:</span> ${item.subtotal}
                </div>
              </div>
              <div className="mt-2">
                <span className="text-gray-500">Description:</span> {item.description}
              </div>
            </div>
          )}

          {/* Feedback Type */}
          <div className="space-y-2">
            <Label htmlFor="feedback_type">Feedback Type</Label>
            <Select
              value={form.watch('feedback_type')}
              onValueChange={(value) => form.setValue('feedback_type', value as any)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select feedback type" />
              </SelectTrigger>
              <SelectContent>
                {feedbackTypeOptions.map((option) => {
                  const Icon = option.icon
                  return (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${option.color}`} />
                        {option.label}
                      </div>
                    </SelectItem>
                  )
                })}
              </SelectContent>
            </Select>
          </div>

          {/* Comment */}
          <div className="space-y-2">
            <Label htmlFor="comment">Comment</Label>
            <Textarea
              id="comment"
              placeholder="Please provide details about your feedback..."
              className="min-h-[100px]"
              {...form.register('comment')}
            />
          </div>

          {/* Conditional Fields Based on Feedback Type */}
          {selectedFeedbackType === 'incorrect' && (
            <div className="space-y-4">
              <h4 className="font-medium">Correction Details</h4>
              <div className="space-y-2">
                <Label htmlFor="suggested_sku">Suggested SKU</Label>
                <Input
                  id="suggested_sku"
                  placeholder="Enter the correct SKU"
                  {...form.register('suggested_sku')}
                />
              </div>
            </div>
          )}

          {selectedFeedbackType === 'wrong_quantity' && (
            <div className="space-y-2">
              <Label htmlFor="suggested_quantity">Suggested Quantity</Label>
              <Input
                id="suggested_quantity"
                type="number"
                min="1"
                placeholder="Enter the correct quantity"
                {...form.register('suggested_quantity', { valueAsNumber: true })}
              />
            </div>
          )}

          {selectedFeedbackType === 'wrong_price' && (
            <div className="space-y-2">
              <Label htmlFor="suggested_price">Suggested Price</Label>
              <Input
                id="suggested_price"
                type="number"
                min="0"
                step="0.01"
                placeholder="Enter the correct price"
                {...form.register('suggested_price', { valueAsNumber: true })}
              />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={createFeedback.isPending}
              className="gap-2"
            >
              {selectedOption && <selectedOption.icon className="h-4 w-4" />}
              {item.id ? 'Submit Feedback' : 'Save Feedback'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
