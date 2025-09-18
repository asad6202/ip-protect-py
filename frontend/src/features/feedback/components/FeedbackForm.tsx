import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Star, Send } from 'lucide-react'
import { useCreateFeedback } from '../api'
import { CreateFeedbackRequest } from '@/lib/types'

const feedbackSchema = z.object({
  rating: z.number().min(1).max(5).optional(),
  comment: z.string().optional(),
  labels: z.string().optional(),
  corrections: z.string().optional(),
})

type FeedbackFormData = z.infer<typeof feedbackSchema>

interface FeedbackFormProps {
  quoteId: string
  onSuccess?: () => void
}

export default function FeedbackForm({ quoteId, onSuccess }: FeedbackFormProps) {
  const [rating, setRating] = useState<number | undefined>(undefined)
  const createFeedback = useCreateFeedback()

  const form = useForm<FeedbackFormData>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      rating: undefined,
      comment: '',
      labels: '',
      corrections: '',
    },
  })

  const onSubmit = async (data: FeedbackFormData) => {
    try {
      const feedbackData: CreateFeedbackRequest = {
        rating: data.rating as 1 | 2 | 3 | 4 | 5 | undefined,
        comment: data.comment || undefined,
        labels: data.labels ? JSON.parse(data.labels) : undefined,
        corrections: data.corrections ? JSON.parse(data.corrections) : undefined,
      }

      await createFeedback.mutateAsync({
        quoteId,
        data: feedbackData,
      })

      form.reset()
      setRating(undefined)
      onSuccess?.()
    } catch (error) {
      console.error('Error creating feedback:', error)
    }
  }

  const StarRating = ({ value, onChange }: { value: number; onChange: (rating: number) => void }) => {
    return (
      <div className="flex space-x-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => {
              onChange(star)
              form.setValue('rating', star)
            }}
            className={`p-1 ${
              star <= value ? 'text-yellow-400' : 'text-gray-300'
            } hover:text-yellow-400 transition-colors`}
          >
            <Star className="h-6 w-6 fill-current" />
          </button>
        ))}
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Provide Feedback</CardTitle>
        <CardDescription>
          Help us improve by sharing your thoughts on this quote
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {/* Rating */}
          <div className="space-y-2">
            <Label>Rating</Label>
            <StarRating
              value={rating || 0}
              onChange={(value) => {
                setRating(value)
                form.setValue('rating', value)
              }}
            />
            {form.formState.errors.rating && (
              <p className="text-sm text-destructive">
                {form.formState.errors.rating.message}
              </p>
            )}
          </div>

          {/* Comment */}
          <div className="space-y-2">
            <Label htmlFor="comment">Comment</Label>
            <Textarea
              id="comment"
              {...form.register('comment')}
              placeholder="Share your thoughts about this quote..."
              className="min-h-[100px]"
            />
            {form.formState.errors.comment && (
              <p className="text-sm text-destructive">
                {form.formState.errors.comment.message}
              </p>
            )}
          </div>

          {/* Labels */}
          <div className="space-y-2">
            <Label htmlFor="labels">Labels (JSON)</Label>
            <Textarea
              id="labels"
              {...form.register('labels')}
              placeholder='{"category": "security", "priority": "high"}'
              className="min-h-[80px] font-mono text-sm"
            />
            {form.formState.errors.labels && (
              <p className="text-sm text-destructive">
                {form.formState.errors.labels.message}
              </p>
            )}
          </div>

          {/* Corrections */}
          <div className="space-y-2">
            <Label htmlFor="corrections">Corrections (JSON)</Label>
            <Textarea
              id="corrections"
              {...form.register('corrections')}
              placeholder='{"items": [{"sku": "ABC123", "suggested_price": 150}]}'
              className="min-h-[80px] font-mono text-sm"
            />
            {form.formState.errors.corrections && (
              <p className="text-sm text-destructive">
                {form.formState.errors.corrections.message}
              </p>
            )}
          </div>

          <Button
            type="submit"
            disabled={createFeedback.isPending}
            className="w-full"
          >
            {createFeedback.isPending ? (
              'Submitting...'
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Submit Feedback
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
