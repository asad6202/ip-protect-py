import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, Save, RotateCcw } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import QuotePromptForm from '../components/QuotePromptForm'
import QuoteItemsEditor from '../components/QuoteItemsEditor'
import { useCreateQuote } from '../api'
import { QuoteItem, QuoteGenResponse } from '@/lib/types'
import { useToast } from '@/components/ui/use-toast'

export default function QuoteCreateFromPromptPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const createQuote = useCreateQuote()

  const [step, setStep] = useState<'prompt' | 'edit'>('prompt')
  const [generatedData, setGeneratedData] = useState<QuoteGenResponse | null>(null)
  const [items, setItems] = useState<QuoteItem[]>([])
  const [notes, setNotes] = useState('')
  const [title, setTitle] = useState('')

  const handleGenerate = (response: QuoteGenResponse) => {
    setGeneratedData(response)
    setItems(response.items)
    setNotes(response.notes || '')
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
        prompt: '', // This would come from the original prompt
        currency: generatedData?.currency || 'USD',
        items,
        notes: notes || undefined,
      })

      toast({
        title: 'Quote created successfully',
        description: 'Your quote has been saved.',
      })

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
    setNotes('')
    setTitle('')
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
        <div className="space-y-6">
          {/* Quote Title */}
          <Card>
            <CardHeader>
              <CardTitle>Quote Details</CardTitle>
              <CardDescription>
                Set a title for this quote
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

          {/* Items Editor */}
          <QuoteItemsEditor
            items={items}
            onItemsChange={setItems}
            currency={generatedData.currency}
            notes={notes}
            onNotesChange={setNotes}
          />
        </div>
      )}
    </div>
  )
}
