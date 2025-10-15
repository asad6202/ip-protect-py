import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Save, RotateCcw } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import QuotePromptForm from '../components/QuotePromptForm'
import QuoteWidget from '../components/QuoteWidget'
import { useCreateQuote } from '../api'
import { QuoteItem, QuoteGenResponse } from '@/lib-utils/types'
import { useToast } from '@/components/ui/use-toast'

export default function QuoteCreateFromPromptPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const createQuote = useCreateQuote()

  const [step, setStep] = useState<'prompt' | 'edit'>('prompt')
  const [generatedData, setGeneratedData] = useState<QuoteGenResponse | null>(null)
  const [items, setItems] = useState<QuoteItem[]>([])
  const [title, setTitle] = useState('')
  const [originalPrompt, setOriginalPrompt] = useState('')

  const handleGenerate = (prompt: string, response: QuoteGenResponse) => {
    setOriginalPrompt(prompt)
    setGeneratedData(response)
    setItems(response.items)
    setStep('edit')
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
      const quote = await createQuote.mutateAsync({
        title: title || undefined,
        prompt: originalPrompt,
        currency: generatedData?.currency || 'USD',
        items,
      })

      toast({
        title: 'Quote created successfully',
        description: 'Your quote has been saved. Use the chat to make modifications.',
      })

      // Navigate to quote detail page where user can use chat to modify
      navigate(`/quotes/${quote.id}`)
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
        <div className="space-y-6 max-w-5xl mx-auto">
          {/* Quote Title Field */}
          <Card>
            <CardHeader>
              <CardTitle>Quote Title</CardTitle>
              <CardDescription>
                Set a title for this quote (optional). After saving, you can use the AI chat to modify items.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter quote title (optional)"
                className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
              />
            </CardContent>
          </Card>

          {/* Quote Widget */}
          <QuoteWidget
            quote={{
              id: 'new-quote',
              prompt: originalPrompt,
              currency: generatedData.currency,
              total_amount: items.reduce((sum, item) => sum + (item.subtotal || 0), 0),
              status: 'draft',
              items: items,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }}
          />
          
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <div className="text-blue-600 text-2xl">💬</div>
                <div>
                  <h3 className="font-semibold text-blue-900 mb-1">Need to make changes?</h3>
                  <p className="text-sm text-blue-700">
                    Save this quote and use the AI-powered chat interface to add, remove, or modify items. 
                    You can even attach images or documents for better context!
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
