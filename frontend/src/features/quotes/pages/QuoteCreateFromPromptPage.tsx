import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Save, RotateCcw } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import QuotePromptForm from '../components/QuotePromptForm'
import QuoteItemsEditor from '../components/QuoteItemsEditor'
import QuoteFeedbackForm from '../components/QuoteFeedbackForm'
import { useCreateQuote } from '../api'
import { useCreateItemFeedback } from '../api-item-feedback'
import { QuoteItem, QuoteGenResponse } from '@/lib-utils/types'
import { useToast } from '@/components/ui/use-toast'
import { formatCurrency } from '@/lib-utils/format'

export default function QuoteCreateFromPromptPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const createQuote = useCreateQuote()
  const createItemFeedback = useCreateItemFeedback()

  const [step, setStep] = useState<'prompt' | 'edit'>('prompt')
  const [generatedData, setGeneratedData] = useState<QuoteGenResponse | null>(null)
  const [items, setItems] = useState<QuoteItem[]>([])
  const [title, setTitle] = useState('')
  const [originalPrompt, setOriginalPrompt] = useState('')
  const [feedback, setFeedback] = useState<any>(null)

  // Debug items changes
  const handleItemsChange = (newItems: QuoteItem[]) => {
    console.log('🎯 Parent: handleItemsChange called with:', newItems)
    console.log('🎯 Parent: items length:', newItems.length)
    console.log('🎯 Parent: current items before update:', items)
    setItems(newItems)
    console.log('🎯 Parent: items state updated')
  }

  // Debug current items
  console.log('🎯 Parent: Current items state:', items)

  const handleGenerate = (prompt: string, response: QuoteGenResponse) => {
    setOriginalPrompt(prompt)
    setGeneratedData(response)
    setItems(response.items)
    setStep('edit')
  }

  const handleFeedback = (feedbackData: any) => {
    setFeedback(feedbackData)
  }

  const handleSave = async () => {
    if (items.length === 0) {
      toast({
        title: 'No items to save',
        description: 'Please add at least one item to the quote.',
        variant: 'destructive',
      })
      return
    }

    try {
      // Extract item-level feedback from items metadata
      const itemFeedbackData = items
        .filter(item => item.metadata?.item_feedback)
        .map(item => ({
          sku: item.metadata?.original_sku || item.sku, // Use original SKU for feedback mapping
          feedback: item.metadata.item_feedback
        }))

      // Prepare feedback data for API
      const feedbackRequest = feedback && feedback.product_feedback ? {
        comment: feedback.product_feedback,
        labels: {
          product_feedback: feedback.product_feedback,
          item_feedback_count: itemFeedbackData.length
        }
      } : undefined

      const quote = await createQuote.mutateAsync({
        title: title || undefined,
        prompt: originalPrompt,
        currency: generatedData?.currency || 'USD',
        items,
        feedback: feedbackRequest,
      })

      // Save item-level feedback after quote is created
      if (itemFeedbackData.length > 0) {
        try {
          // Find the corresponding quote items by SKU and save feedback
          for (const itemFeedback of itemFeedbackData) {
            // Find quote item by original SKU (for replaced items) or current SKU (for non-replaced items)
            const quoteItem = quote.items?.find(item => {
              // If this item was replaced, check if the original SKU matches
              if (item.metadata?.original_sku) {
                return item.metadata.original_sku === itemFeedback.sku
              }
              // Otherwise, check the current SKU
              return item.sku === itemFeedback.sku
            })
            
            if (quoteItem?.id) {
              await createItemFeedback.mutateAsync({
                itemId: quoteItem.id,
                data: itemFeedback.feedback
              })
            }
          }
          console.log('Item feedback saved successfully')
        } catch (error) {
          console.error('Failed to save item feedback:', error)
          // Don't fail the entire quote creation if feedback saving fails
        }
      }

      const feedbackCount = itemFeedbackData.length
      const hasGeneralFeedback = feedback && feedback.product_feedback
      
      toast({
        title: 'Quote created successfully',
        description: feedbackCount > 0 || hasGeneralFeedback 
          ? `Your quote has been saved with ${feedbackCount > 0 ? `${feedbackCount} item feedback${feedbackCount > 1 ? 's' : ''}` : ''}${feedbackCount > 0 && hasGeneralFeedback ? ' and ' : ''}${hasGeneralFeedback ? 'general feedback' : ''}.`
          : 'Your quote has been saved.',
      })

      // Small delay to ensure cache invalidation completes
      setTimeout(() => {
        navigate(`/quotes/${quote.id}`)
      }, 100)
    } catch (error) {
      toast({
        title: 'Error creating quote',
        description: 'There was an error saving the quote. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const handleReset = () => {
    setStep('prompt')
    setGeneratedData(null)
    setItems([])
    setTitle('')
    setOriginalPrompt('')
    setFeedback(null)
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Create Quote"
        description="Generate a quote from your requirements"
        showBackButton
        children={
          step === 'edit' && (
            <div className="flex space-x-2">
              <Button variant="outline" onClick={handleReset}>
                <RotateCcw className="mr-2 h-4 w-4" />
                Start Over
              </Button>
              <Button onClick={handleSave} disabled={createQuote.isPending}>
                <Save className="mr-2 h-4 w-4" />
                Save Quote
              </Button>
            </div>
          )
        }
      />

      {step === 'prompt' && (
        <div className="max-w-2xl">
          <QuotePromptForm
            onGenerate={handleGenerate}
            isLoading={createQuote.isPending}
          />
        </div>
      )}

      {step === 'edit' && generatedData && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Quote Details with Total */}
            <Card>
              <CardHeader>
                <CardTitle>Quote Details</CardTitle>
                <CardDescription>
                  Set a title for this quote
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-1 block">Quote Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter quote title (optional)"
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-1 block">Original Prompt</label>
                  <div className="text-sm p-3 bg-muted rounded-md border">
                    {originalPrompt}
                  </div>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between items-center">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Total</label>
                      <p className="text-2xl font-bold">
                        {formatCurrency(items.reduce((sum, item) => sum + (item.subtotal || 0), 0), generatedData.currency)}
                      </p>
                    </div>
                    <div className="text-right">
                      <label className="text-sm font-medium text-muted-foreground">Items</label>
                      <p className="text-lg font-semibold">
                        {items.length} item{items.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Items Editor */}
            <QuoteItemsEditor
              items={items}
              onItemsChange={handleItemsChange}
              currency={generatedData.currency}
            />
          </div>

          {/* Right Sidebar - Sticky Feedback */}
          <div className="lg:col-span-1">
            <div className="sticky top-6">
              <QuoteFeedbackForm
                onFeedback={handleFeedback}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
