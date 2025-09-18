import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Star, Send, AlertCircle, CheckCircle, XCircle, HelpCircle } from 'lucide-react'
import { useCreateFeedback } from '../api'
import { CreateFeedbackRequest } from '@/lib/types'

const feedbackSchema = z.object({
  rating: z.number().min(1).max(5).optional(),
  comment: z.string().optional(),
  accuracy: z.enum(['excellent', 'good', 'fair', 'poor']).optional(),
  issues: z.string().optional(),
  suggestions: z.string().optional(),
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
      accuracy: undefined,
      issues: '',
      suggestions: '',
    },
  })

  const onSubmit = async (data: FeedbackFormData) => {
    try {
      // Prepare structured feedback data for GPT improvement
      const structuredFeedback = {
        accuracy: data.accuracy,
        issues: data.issues || undefined,
        suggestions: data.suggestions || undefined,
      }

      const feedbackData: CreateFeedbackRequest = {
        rating: data.rating as 1 | 2 | 3 | 4 | 5 | undefined,
        comment: data.comment || undefined,
        labels: structuredFeedback,
      }

      await createFeedback.mutateAsync({
        quoteId,
        data: feedbackData,
      })

      form.reset({
        rating: undefined,
        comment: '',
        accuracy: undefined,
        issues: '',
        suggestions: '',
      })
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
        <CardTitle className="flex items-center gap-2">
          <HelpCircle className="h-5 w-5" />
          Quick Feedback
        </CardTitle>
        <CardDescription>
          Help us improve by sharing your thoughts on this quote
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Overall Rating */}
          <div className="space-y-2">
            <Label className="text-base font-medium">How would you rate this quote?</Label>
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

          {/* Accuracy Assessment */}
          <div className="space-y-2">
            <Label htmlFor="accuracy" className="text-base font-medium">How accurate was the product selection?</Label>
            <Select
              value={form.watch('accuracy')}
              onValueChange={(value) => form.setValue('accuracy', value as any)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select accuracy level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="excellent">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    Excellent - Perfect match
                  </div>
                </SelectItem>
                <SelectItem value="good">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-500" />
                    Good - Mostly accurate
                  </div>
                </SelectItem>
                <SelectItem value="fair">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                    Fair - Some issues
                  </div>
                </SelectItem>
                <SelectItem value="poor">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-red-500" />
                    Poor - Many issues
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Issues - Combined field */}
          <div className="space-y-2">
            <Label htmlFor="issues" className="text-base font-medium">Any issues or problems?</Label>
            <Textarea
              id="issues"
              {...form.register('issues')}
              placeholder="Tell us about any missing products, incorrect items, pricing issues, or other problems..."
              className="min-h-[100px]"
            />
          </div>

          {/* Suggestions */}
          <div className="space-y-2">
            <Label htmlFor="suggestions" className="text-base font-medium">Suggestions for improvement</Label>
            <Textarea
              id="suggestions"
              {...form.register('suggestions')}
              placeholder="How can we make this better? Any suggestions?"
              className="min-h-[80px]"
            />
          </div>

          {/* General Comment */}
          <div className="space-y-2">
            <Label htmlFor="comment" className="text-base font-medium">Additional comments (optional)</Label>
            <Textarea
              id="comment"
              {...form.register('comment')}
              placeholder="Any other feedback or comments..."
              className="min-h-[80px]"
            />
          </div>

          <Button
            type="submit"
            disabled={createFeedback.isPending}
            className="w-full"
            size="lg"
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
