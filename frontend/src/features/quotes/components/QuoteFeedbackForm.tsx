import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { MessageSquare } from 'lucide-react'

const feedbackSchema = z.object({
  product_feedback: z.string().optional(),
})

type FeedbackFormData = z.infer<typeof feedbackSchema>

interface QuoteFeedbackFormProps {
  onFeedback: (feedback: FeedbackFormData) => void
}

export default function QuoteFeedbackForm({ onFeedback }: QuoteFeedbackFormProps) {
  const form = useForm<FeedbackFormData>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      product_feedback: '',
    },
  })

  const handleChange = (value: string) => {
    form.setValue('product_feedback', value)
    onFeedback({ product_feedback: value })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Quick Feedback
        </CardTitle>
        <CardDescription>
          Help us improve by providing feedback on this quote. Any feedback will be saved with the quote.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Product Feedback */}
          <div className="space-y-2">
            <Label htmlFor="product_feedback">Product Feedback (Optional)</Label>
            <Textarea
              id="product_feedback"
              placeholder="e.g., 'This product should be returned instead of that one' or 'Add more outdoor cameras'"
              className="min-h-[100px]"
              {...form.register('product_feedback')}
              onChange={(e) => handleChange(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Tell us if any products should be different or if something is missing. This helps us improve future quotes.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
