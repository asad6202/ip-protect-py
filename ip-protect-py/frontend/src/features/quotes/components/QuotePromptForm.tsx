import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'
import { useGenerateQuote } from '../api'

const promptSchema = z.object({
  prompt: z.string().min(10, 'Prompt must be at least 10 characters'),
})

type PromptFormData = z.infer<typeof promptSchema>

interface QuotePromptFormProps {
  onGenerate: (prompt: string, response: any) => void
  isLoading?: boolean
}

export default function QuotePromptForm({ onGenerate, isLoading }: QuotePromptFormProps) {
  const generateQuote = useGenerateQuote()

  const form = useForm<PromptFormData>({
    resolver: zodResolver(promptSchema),
    defaultValues: {
      prompt: '',
    },
  })

  const onSubmit = async (data: PromptFormData) => {
    try {
      const response = await generateQuote.mutateAsync(data.prompt)
      onGenerate(data.prompt, response)
    } catch (error) {
      console.error('Error generating quote:', error)
    }
  }

  const isSubmitting = generateQuote.isPending || isLoading

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generate Quote</CardTitle>
        <CardDescription>
          Describe what you need and we'll generate a quote with recommended products.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prompt">Requirements *</Label>
            <Textarea
              id="prompt"
              placeholder="Describe your security system requirements... (e.g., 'Need 4 outdoor IP cameras with night vision for a retail store, PoE powered, 4MP resolution')"
              className="min-h-[120px]"
              {...form.register('prompt')}
            />
            {form.formState.errors.prompt && (
              <p className="text-sm text-destructive">
                {form.formState.errors.prompt.message}
              </p>
            )}
          </div>


          <Button
            type="submit"
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating Quote...
              </>
            ) : (
              'Generate Quote'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
