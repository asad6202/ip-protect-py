import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Save, RotateCcw } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import QuotePromptForm from '../components/QuotePromptForm'
import QuoteWidget from '../components/QuoteWidget'
import QuoteChatInterface from '../components/QuoteChatInterface'
import { useCreateQuote, useGetQuote } from '../api'
import { QuoteItem, QuoteGenResponse } from '@/lib-utils/types'
import { useToast } from '@/components/ui/use-toast'

export default function QuoteCreateFromPromptPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const createQuote = useCreateQuote()

  const [step, setStep] = useState<'prompt' | 'edit'>('prompt')
  const [generatedData, setGeneratedData] = useState<QuoteGenResponse | null>(null)
  const [items, setItems] = useState<QuoteItem[]>([])
  const [originalPrompt, setOriginalPrompt] = useState('')
  const [quoteId, setQuoteId] = useState<string | null>(null)
  
  // Fetch quote data for updates
  const { data: quoteData, refetch: refetchQuote } = useGetQuote(quoteId || '')

  const handleGenerate = async (prompt: string, response: QuoteGenResponse) => {
    setOriginalPrompt(prompt)
    setGeneratedData(response)
    setItems(response.items)
    
    // Auto-save as draft so chat interface can work immediately
    try {
      const quote = await createQuote.mutateAsync({
        title: undefined,
        prompt: prompt,
        currency: response.currency || 'USD',
        items: response.items,
      })
      
      setQuoteId(quote.id)
      setStep('edit')
      
      toast({
        title: 'Quote generated',
        description: 'Use the chat below to modify items or save when ready.',
      })
    } catch (error) {
      toast({
        title: 'Error creating quote',
        description: 'There was an error. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const handleSave = () => {
    // Quote is already saved, just navigate to it
    if (quoteId) {
      toast({
        title: 'Quote ready',
        description: 'Your quote has been saved successfully.',
      })
      navigate(`/quotes/${quoteId}`)
    }
  }

  const handleReset = () => {
    setStep('prompt')
    setGeneratedData(null)
    setItems([])
    setOriginalPrompt('')
    setQuoteId(null)
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
              <Button onClick={handleSave} disabled={!quoteId}>
                <Save className="mr-2 h-4 w-4" />
                Finish & View Quote
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
          {/* Quote Widget - use quoteData if available, otherwise use local state */}
          <QuoteWidget
            quote={quoteData || {
              id: quoteId || 'new-quote',
              prompt: originalPrompt,
              currency: generatedData.currency,
              total_amount: items.reduce((sum, item) => sum + (item.subtotal || 0), 0),
              status: 'draft',
              items: items,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }}
          />
          
          {/* AI Chat Interface for Quote Modifications */}
          {quoteId && (
            <QuoteChatInterface 
              quoteId={quoteId}
              onQuoteUpdated={async () => {
                // Refetch the updated quote data
                const result = await refetchQuote()
                if (result.data && generatedData) {
                  setItems(result.data.items || [])
                  setGeneratedData({
                    ...generatedData,
                    items: result.data.items || [],
                    total: result.data.total_amount || 0,
                    currency: result.data.currency || 'USD'
                  })
                }
              }}
            />
          )}
        </div>
      )}
    </div>
  )
}
