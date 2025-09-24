import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, Lightbulb, Wand2, Code, CheckCircle } from 'lucide-react'
import { useCreateRule } from '../api'
import api from '@/lib-utils/api'

const nlpRuleSchema = z.object({
  command: z.string().min(1, 'Command is required'),
  name: z.string().optional(),
})

type NLPRuleFormData = z.infer<typeof nlpRuleSchema>

interface NLPRuleFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  ruleSetId: string
  onSuccess?: () => void
}

interface ParsedRule {
  name: string
  condition: Record<string, any>
  actions: Record<string, any>
  scope: string
  priority: number
}

interface RuleTemplate {
  name: string
  command: string
  description: string
}

export default function NLPRuleForm({ 
  open, 
  onOpenChange, 
  ruleSetId,
  onSuccess 
}: NLPRuleFormProps) {
  const [isParsing, setIsParsing] = useState(false)
  const [parsedRule, setParsedRule] = useState<ParsedRule | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [templates, setTemplates] = useState<RuleTemplate[]>([])
  const [showTemplates, setShowTemplates] = useState(false)
  
  const createRule = useCreateRule()
  
  const form = useForm<NLPRuleFormData>({
    resolver: zodResolver(nlpRuleSchema),
    defaultValues: {
      command: '',
      name: '',
    },
  })

  // Load templates on mount
  useEffect(() => {
    if (open) {
      loadTemplates()
    }
  }, [open])

  // Load suggestions when command changes
  useEffect(() => {
    const command = form.watch('command')
    if (command && command.length > 2) {
      loadSuggestions(command)
    } else {
      setSuggestions([])
    }
  }, [form.watch('command')])

  const loadTemplates = async () => {
    try {
      const response = await api.get('/v1/rule-templates')
      setTemplates(response.data)
    } catch (error) {
      console.error('Failed to load templates:', error)
    }
  }

  const loadSuggestions = async (partialCommand: string) => {
    try {
      const response = await api.post('/v1/nlp-suggestions', {
        partial_command: partialCommand
      })
      setSuggestions(response.data.suggestions)
    } catch (error) {
      console.error('Failed to load suggestions:', error)
    }
  }

  const parseCommand = async (command: string) => {
    if (!command.trim()) return
    
    setIsParsing(true)
    try {
      const response = await api.post('/v1/parse-nlp-rule', {
        command,
        rule_set_id: ruleSetId
      })
      setParsedRule(response.data)
      form.setValue('name', response.data.name)
    } catch (error) {
      console.error('Failed to parse command:', error)
    } finally {
      setIsParsing(false)
    }
  }

  const applyTemplate = (template: RuleTemplate) => {
    form.setValue('command', template.command)
    setShowTemplates(false)
    parseCommand(template.command)
  }

  const applySuggestion = (suggestion: string) => {
    form.setValue('command', suggestion)
    setSuggestions([])
    parseCommand(suggestion)
  }

  const onSubmit = async (data: NLPRuleFormData) => {
    if (!parsedRule) {
      await parseCommand(data.command)
      return
    }

    try {
      const ruleData = {
        rule_set_id: ruleSetId,
        name: data.name || parsedRule.name,
        active: true,
        scope: parsedRule.scope as "global" | "item",
        priority: parsedRule.priority,
        condition: parsedRule.condition,
        actions: parsedRule.actions,
      }

      await createRule.mutateAsync(ruleData)
      form.reset()
      setParsedRule(null)
      setSuggestions([])
      onSuccess?.()
      onOpenChange(false)
    } catch (error) {
      console.error('Error creating rule:', error)
    }
  }

  const handleCommandChange = (command: string) => {
    form.setValue('command', command)
    if (command.trim()) {
      parseCommand(command)
    } else {
      setParsedRule(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5" />
            Create Rule with Natural Language
          </DialogTitle>
          <DialogDescription>
            Describe your rule in plain English and we'll convert it to the proper format.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Section */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="command">Rule Command *</Label>
              <div className="relative">
                <Textarea
                  id="command"
                  placeholder="e.g., Prefer Axis cameras, Avoid PTZ cameras, Require outdoor cameras only..."
                  className="min-h-[100px]"
                  {...form.register('command')}
                  onChange={(e) => handleCommandChange(e.target.value)}
                />
                {isParsing && (
                  <div className="absolute top-2 right-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                )}
              </div>
              {form.formState.errors.command && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.command.message}
                </p>
              )}
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && (
              <div className="space-y-2">
                <Label className="text-sm font-medium">Suggestions</Label>
                <div className="space-y-1">
                  {suggestions.map((suggestion, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start text-left h-auto p-2"
                      onClick={() => applySuggestion(suggestion)}
                    >
                      <Lightbulb className="h-3 w-3 mr-2" />
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Templates */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">Templates</Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowTemplates(!showTemplates)}
                >
                  {showTemplates ? 'Hide' : 'Show'} Templates
                </Button>
              </div>
              {showTemplates && (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {templates.map((template, index) => (
                    <Card key={index} className="cursor-pointer hover:bg-muted/50" onClick={() => applyTemplate(template)}>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">{template.name}</CardTitle>
                        <CardDescription className="text-xs">{template.description}</CardDescription>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <code className="text-xs bg-muted px-2 py-1 rounded">{template.command}</code>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">Rule Name (Optional)</Label>
              <Input
                id="name"
                placeholder="Custom rule name"
                {...form.register('name')}
              />
            </div>
          </div>

          {/* Preview Section */}
          <div className="space-y-4">
            <Label className="text-sm font-medium">Parsed Rule Preview</Label>
            
            {parsedRule ? (
              <div className="space-y-4">
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">{parsedRule.name}</CardTitle>
                      <div className="flex gap-2">
                        <Badge variant={parsedRule.scope === 'global' ? 'default' : 'secondary'}>
                          {parsedRule.scope}
                        </Badge>
                        <Badge variant="outline">Priority: {parsedRule.priority}</Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium text-muted-foreground">Condition</Label>
                      <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-x-auto">
                        {JSON.stringify(parsedRule.condition, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <Label className="text-xs font-medium text-muted-foreground">Actions</Label>
                      <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-x-auto">
                        {JSON.stringify(parsedRule.actions, null, 2)}
                      </pre>
                    </div>
                  </CardContent>
                </Card>
                
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Rule parsed successfully! Ready to create.
                </div>
              </div>
            ) : (
              <Card>
                <CardContent className="py-8 text-center">
                  <Code className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Enter a command above to see the parsed rule preview
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={form.handleSubmit(onSubmit)}
            disabled={!parsedRule || createRule.isPending}
          >
            {createRule.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Rule'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
