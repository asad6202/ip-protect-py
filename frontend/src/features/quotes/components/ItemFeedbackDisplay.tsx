import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ThumbsUp, ThumbsDown, AlertCircle, DollarSign, Hash, Package, MessageSquare } from 'lucide-react'
import { QuoteItemFeedback } from '@/lib-utils/types'

interface ItemFeedbackDisplayProps {
  feedback: QuoteItemFeedback[]
  itemId: string
}

const feedbackTypeConfig = {
  correct: { icon: ThumbsUp, color: 'bg-green-100 text-green-800', label: 'Correct' },
  incorrect: { icon: ThumbsDown, color: 'bg-red-100 text-red-800', label: 'Incorrect' },
  missing: { icon: AlertCircle, color: 'bg-orange-100 text-orange-800', label: 'Missing' },
  wrong_quantity: { icon: Hash, color: 'bg-blue-100 text-blue-800', label: 'Wrong Quantity' },
  wrong_price: { icon: DollarSign, color: 'bg-purple-100 text-purple-800', label: 'Wrong Price' },
  wrong_specs: { icon: Package, color: 'bg-gray-100 text-gray-800', label: 'Wrong Specs' },
}

export default function ItemFeedbackDisplay({ feedback, itemId }: ItemFeedbackDisplayProps) {
  if (!feedback || feedback.length === 0) {
    return null
  }

  const latestFeedback = feedback[0] // Most recent feedback
  const config = feedbackTypeConfig[latestFeedback.feedback_type]

  return (
    <Card className="mt-2">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Item Feedback
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Latest Feedback */}
        <div className="flex items-center gap-2">
          <Badge className={config.color}>
            <config.icon className="h-3 w-3 mr-1" />
            {config.label}
          </Badge>
          {latestFeedback.rating && (
            <Badge variant="outline">
              {latestFeedback.rating} {latestFeedback.rating === 1 ? 'star' : 'stars'}
            </Badge>
          )}
        </div>

        {/* Comment */}
        {latestFeedback.comment && (
          <p className="text-sm text-gray-700">{latestFeedback.comment}</p>
        )}

        {/* Suggestions */}
        {(latestFeedback.suggested_sku || latestFeedback.suggested_quantity || latestFeedback.suggested_price) && (
          <div className="space-y-2">
            <h5 className="text-xs font-medium text-gray-600 uppercase tracking-wide">Suggestions</h5>
            <div className="space-y-1 text-sm">
              {latestFeedback.suggested_sku && (
                <div>
                  <span className="text-gray-500">Suggested SKU:</span> {latestFeedback.suggested_sku}
                </div>
              )}
              {latestFeedback.suggested_quantity && (
                <div>
                  <span className="text-gray-500">Suggested Quantity:</span> {latestFeedback.suggested_quantity}
                </div>
              )}
              {latestFeedback.suggested_price && (
                <div>
                  <span className="text-gray-500">Suggested Price:</span> ${latestFeedback.suggested_price}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Historical Feedback Count */}
        {feedback.length > 1 && (
          <div className="text-xs text-gray-500">
            +{feedback.length - 1} more feedback entries
          </div>
        )}
      </CardContent>
    </Card>
  )
}
