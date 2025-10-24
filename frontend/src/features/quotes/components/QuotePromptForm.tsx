import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Paperclip, X } from 'lucide-react'
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
  const [attachments, setAttachments] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const form = useForm<PromptFormData>({
    resolver: zodResolver(promptSchema),
    defaultValues: {
      prompt: '',
    },
  })

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setAttachments(prev => [...prev, ...files])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const onSubmit = async (data: PromptFormData) => {
    try {
      const response = await generateQuote.mutateAsync({
        prompt: data.prompt,
        attachments
      })
      onGenerate(data.prompt, response)
      setAttachments([])
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
          Describe your requirements or attach files (images, PDFs, documents) with product details. AI will generate quotes directly from your attachments.
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

          <div className="space-y-2">
            <Label>Attachments (Optional)</Label>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip className="mr-2 h-4 w-4" />
                Add Files
              </Button>
              <span className="text-sm text-muted-foreground">
                Images, PDFs, or documents with product details
              </span>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              multiple
              accept="image/*,.pdf,.doc,.docx,.txt"
              onChange={handleFileSelect}
            />
            
            {attachments.length > 0 && (
              <div className="space-y-2 mt-2">
                {attachments.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-muted rounded-md"
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <Paperclip className="h-4 w-4 flex-shrink-0" />
                      <span className="text-sm truncate">{file.name}</span>
                      <span className="text-xs text-muted-foreground flex-shrink-0">
                        ({(file.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAttachment(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
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
