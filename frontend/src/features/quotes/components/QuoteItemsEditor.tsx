import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Trash2, Plus } from 'lucide-react'
import { QuoteItem } from '@/lib/types'
import { formatCurrency } from '@/lib/format'

interface QuoteItemsEditorProps {
  items: QuoteItem[]
  onItemsChange: (items: QuoteItem[]) => void
  currency?: string
  notes?: string
  onNotesChange?: (notes: string) => void
}

export default function QuoteItemsEditor({
  items,
  onItemsChange,
  currency = 'USD',
  notes = '',
  onNotesChange,
}: QuoteItemsEditorProps) {
  const [localItems, setLocalItems] = useState<QuoteItem[]>(items)

  useEffect(() => {
    setLocalItems(items)
  }, [items])

  const updateItem = (index: number, field: keyof QuoteItem, value: any) => {
    const newItems = [...localItems]
    const item = { ...newItems[index] }
    
    if (field === 'quantity' || field === 'unit_price') {
      const numValue = parseFloat(value) || 0
      item[field] = numValue
      item.subtotal = item.quantity * item.unit_price
    } else {
      item[field] = value
    }
    
    newItems[index] = item
    setLocalItems(newItems)
    onItemsChange(newItems)
  }

  const removeItem = (index: number) => {
    const newItems = localItems.filter((_, i) => i !== index)
    setLocalItems(newItems)
    onItemsChange(newItems)
  }

  const addItem = () => {
    const newItem: QuoteItem = {
      sku: '',
      description: '',
      quantity: 1,
      unit_price: 0,
      currency,
      subtotal: 0,
    }
    const newItems = [...localItems, newItem]
    setLocalItems(newItems)
    onItemsChange(newItems)
  }


  return (
    <div className="space-y-6">
      {/* Items Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Quote Items</CardTitle>
              <CardDescription>
                Review and edit the generated quote items
              </CardDescription>
            </div>
            <Button onClick={addItem} size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Item
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {localItems.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No items in this quote. Click "Add Item" to get started.
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-24">Qty</TableHead>
                    <TableHead className="w-32">Unit Price</TableHead>
                    <TableHead className="w-32">Subtotal</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {localItems.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Input
                          value={item.sku}
                          onChange={(e) => updateItem(index, 'sku', e.target.value)}
                          placeholder="SKU"
                          className="font-mono text-sm"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          value={item.description}
                          onChange={(e) => updateItem(index, 'description', e.target.value)}
                          placeholder="Description"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="1"
                          value={item.quantity}
                          onChange={(e) => updateItem(index, 'quantity', e.target.value)}
                          className="text-right"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.unit_price}
                          onChange={(e) => updateItem(index, 'unit_price', e.target.value)}
                          className="text-right"
                        />
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(item.subtotal, currency)}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeItem(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>


      {/* Notes */}
      {onNotesChange && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
            <CardDescription>
              Add any additional notes or comments for this quote
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              value={notes}
              onChange={(e) => onNotesChange(e.target.value)}
              placeholder="Add notes about this quote..."
              className="min-h-[100px]"
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
