import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Trash2, Search, MessageSquare } from 'lucide-react'
import { QuoteItem, Product } from '@/lib-utils/types'
import { formatCurrency } from '@/lib-utils/format'
import ProductSearchDialog from './ProductSearchDialog'
import ItemFeedbackDialog from './ItemFeedbackDialog'

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
  const [searchDialogOpen, setSearchDialogOpen] = useState(false)
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null)
  const [pendingSearchItem, setPendingSearchItem] = useState<boolean>(false)
  const isProcessingSelectionRef = useRef<boolean>(false)

  // Wrapper to debug onItemsChange calls
  const handleItemsChange = (newItems: QuoteItem[]) => {
    console.log('📤 QuoteItemsEditor: calling onItemsChange with:', newItems)
    console.log('📤 QuoteItemsEditor: newItems length:', newItems.length)
    onItemsChange(newItems)
  }

  // Only sync with parent items on initial load
  useEffect(() => {
    console.log('🔄 useEffect: items changed, syncing localItems')
    console.log('🔄 Parent items:', items)
    console.log('🔄 Local items before sync:', localItems)
    setLocalItems(items)
  }, [items])

  const updateItem = (index: number, field: keyof QuoteItem, value: string | number) => {
    const newItems = [...localItems]
    const item = { ...newItems[index] }
    
    if (field === 'quantity' || field === 'unit_price') {
      const numValue = parseFloat(value.toString()) || 0
      if (field === 'quantity') {
        item.quantity = numValue
      } else {
        item.unit_price = numValue
      }
      item.subtotal = item.quantity * item.unit_price
    } else if (field === 'sku' || field === 'description' || field === 'currency') {
      item[field] = value as string
    }
    
    newItems[index] = item
    setLocalItems(newItems)
    handleItemsChange(newItems)
  }

  // Check if an item is a "not found" product
  const isProductNotFound = (item: QuoteItem) => {
    return item.description.includes('Product not found') || 
           item.description.includes('not found') ||
           (item.unit_price === 0 && item.sku && !item.product_id)
  }

  const removeItem = (index: number) => {
    const newItems = localItems.filter((_, i) => i !== index)
    setLocalItems(newItems)
    handleItemsChange(newItems)
  }

  const handleItemFeedbackChange = (itemSku: string, feedback: any) => {
    const newItems = localItems.map(item => {
      if (item.sku === itemSku) {
        return {
          ...item,
          metadata: {
            ...item.metadata,
            item_feedback: feedback
          }
        }
      }
      return item
    })
    setLocalItems(newItems)
    handleItemsChange(newItems)
  }

  const addEmptyItem = () => {
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
    handleItemsChange(newItems)
    return newItems.length - 1 // Return the index of the new item
  }

  const openProductSearch = (itemIndex: number, isNewItem: boolean = false) => {
    setEditingItemIndex(itemIndex)
    setPendingSearchItem(isNewItem)
    setSearchDialogOpen(true)
  }

  const handleProductSelect = (product: Product) => {
    console.log('handleProductSelect called with:', product)
    console.log('editingItemIndex:', editingItemIndex)
    console.log('localItems:', localItems)
    
    // Set flag to prevent dialog close handler from interfering
    isProcessingSelectionRef.current = true
    console.log('🔒 Set isProcessingSelectionRef to true')
    
    if (editingItemIndex !== null) {
      const newItems = [...localItems]
      const item = { ...newItems[editingItemIndex] }
      
      // Store the original "Product not found" SKU for feedback purposes
      const originalSku = item.sku; // This is the original "Product not found" SKU
      
      console.log('Manual replacement - Original SKU:', originalSku, 'Replacement SKU:', product.sku);
      
      // Update the item with replacement product details for database storage
      item.sku = product.sku // Store replacement SKU in database
      item.description = product.description
      item.unit_price = product.price
      item.currency = product.currency
      item.subtotal = item.quantity * item.unit_price
      item.product_id = product.id
      
      // Store original SKU in metadata for feedback purposes
      item.metadata = {
        ...item.metadata,
        search_method: 'manual',
        is_manual_replacement: true,
        original_sku: originalSku, // Keep original "Product not found" SKU for feedback
        replacement_sku: product.sku, // Store the replacement SKU
        replacement_description: product.description, // Store replacement description
        replacement_price: product.price, // Store replacement price
        replacement_currency: product.currency, // Store replacement currency
        replaced_at: new Date().toISOString()
      }
      
      newItems[editingItemIndex] = item
      console.log('Updated item:', item)
      console.log('New items array:', newItems)
      
      setLocalItems(newItems)
      handleItemsChange(newItems)
      console.log('State updated!')
      
      // Reset state after successful update
      setEditingItemIndex(null)
      setPendingSearchItem(false)
    } else {
      console.log('ERROR: editingItemIndex is null!')
    }
    
    // Close dialog after everything is done
    setSearchDialogOpen(false)
    
    // Reset processing flag after dialog close
    setTimeout(() => {
      isProcessingSelectionRef.current = false
      console.log('🔓 Set isProcessingSelectionRef to false')
    }, 200)
  }

  const handleDialogClose = (open: boolean) => {
    console.log('🚪 handleDialogClose called with open:', open)
    console.log('🚪 pendingSearchItem:', pendingSearchItem)
    console.log('🚪 editingItemIndex:', editingItemIndex)
    console.log('🚪 isProcessingSelectionRef.current:', isProcessingSelectionRef.current)
    
    // Only remove pending item if dialog is being closed AND we haven't already processed a product selection
    if (!open && pendingSearchItem && editingItemIndex !== null && !isProcessingSelectionRef.current) {
      console.log('🚪 Removing pending item due to cancel')
      // Remove the pending item if user cancels
      const newItems = localItems.filter((_, i) => i !== editingItemIndex)
      setLocalItems(newItems)
      handleItemsChange(newItems)
    } else if (isProcessingSelectionRef.current) {
      console.log('🚪 Skipping cancel logic - processing selection')
    }
    
    setSearchDialogOpen(open)
    
    // Only reset state if dialog is being closed
    if (!open) {
      setEditingItemIndex(null)
      setPendingSearchItem(false)
    }
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
            <Button 
              onClick={() => {
                // Add a new empty item and open search for it
                const newItemIndex = addEmptyItem()
                console.log('Opening search dialog for index:', newItemIndex)
                openProductSearch(newItemIndex, true)
              }} 
              size="sm"
            >
              <Search className="mr-2 h-4 w-4" />
              Add from Catalog
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {localItems.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No items in this quote. Click "Add from Catalog" to search and add products.
            </div>
          ) : (
            <div className="space-y-4">
              {localItems.some(item => isProductNotFound(item)) && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <div className="text-amber-600">⚠️</div>
                    <div className="flex-1">
                      <h4 className="text-sm font-medium text-amber-800">Some products not found in catalog</h4>
                      <p className="text-sm text-amber-700 mt-1">
                        Highlighted items were not found in the product catalog. You can either:
                      </p>
                      <ul className="text-sm text-amber-700 mt-2 ml-4 list-disc">
                        <li>Search and replace with a catalog product using "Search Catalog"</li>
                        <li>Keep the manual entry and save the quote as-is</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-24">Qty</TableHead>
                    <TableHead className="w-32">Unit Price</TableHead>
                    <TableHead className="w-32">Subtotal</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {localItems.map((item, index) => {
                    const isNotFound = isProductNotFound(item)
                    const isFeedbackLearning = item.metadata?.is_feedback_learning
                    return (
                      <TableRow 
                        key={index} 
                        className={
                          isNotFound ? 'bg-red-50 border-red-200' : 
                          isFeedbackLearning ? 'bg-green-50 border-green-200' : ''
                        }
                      >
                        <TableCell>
                          <div className="flex space-x-2">
                            <Input
                              value={item.metadata?.is_manual_replacement ? item.metadata.original_sku : item.sku}
                              onChange={(e) => updateItem(index, 'sku', e.target.value)}
                              placeholder="SKU"
                              className={`font-mono text-sm ${isNotFound ? 'border-red-300 bg-red-50' : ''}`}
                            />
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => openProductSearch(index)}
                              className="shrink-0"
                            >
                              <Search className="h-4 w-4" />
                            </Button>
                          </div>
                          {/* Show replacement SKU if available */}
                          {item.metadata?.is_manual_replacement && item.metadata?.replacement_sku && (
                            <div className="text-xs text-green-600 mt-1">
                              Replaced with: <span className="font-mono">{item.sku}</span>
                            </div>
                          )}
                          {/* Show feedback learning indicator */}
                          {item.metadata?.is_feedback_learning && item.metadata?.replacement_sku && (
                            <div className="text-xs text-blue-600 mt-1 flex items-center gap-1">
                              <span>🧠</span>
                              <span>Learned from feedback: <span className="font-mono">{item.metadata.replacement_sku}</span></span>
                            </div>
                          )}
                        </TableCell>
                      <TableCell>
                        <div className="space-y-2">
                          <Input
                            value={item.description}
                            onChange={(e) => updateItem(index, 'description', e.target.value)}
                            placeholder="Description"
                            className={isNotFound ? 'border-red-300 bg-red-50' : ''}
                          />
                          {isNotFound && (
                            <div className="text-xs text-red-600 flex items-center space-x-2">
                              <span>⚠️ Product not found in catalog</span>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openProductSearch(index)}
                                className="text-xs h-6 px-2"
                              >
                                Search Catalog
                              </Button>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="1"
                          value={item.quantity}
                          onChange={(e) => updateItem(index, 'quantity', e.target.value)}
                          className={`text-right ${isNotFound ? 'border-red-300 bg-red-50' : ''}`}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.unit_price}
                          onChange={(e) => updateItem(index, 'unit_price', e.target.value)}
                          className={`text-right ${isNotFound ? 'border-red-300 bg-red-50' : ''}`}
                        />
                      </TableCell>
                      <TableCell className={`text-right font-medium ${isNotFound ? 'text-red-600' : ''}`}>
                        {formatCurrency(item.subtotal, currency)}
                        {isNotFound && (
                          <div className="text-xs text-red-500 mt-1">
                            Manual entry
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-1">
                          <ItemFeedbackDialog 
                            item={item} 
                            originalItem={(() => {
                              // If this item was manually replaced, show the original "Product not found" item for feedback
                              const hasReplacement = item.metadata?.is_manual_replacement || 
                                                   item.metadata?.feedback_corrected || 
                                                   item.metadata?.replacement_sku;
                              
                              console.log('Feedback dialog - Item SKU:', item.sku, 'Has replacement:', hasReplacement, 'Metadata:', item.metadata);
                              
                              // If this item was replaced, show the original "Product not found" item for feedback
                              if (hasReplacement && item.metadata?.original_sku) {
                                console.log('Feedback dialog - Showing original "Product not found" item for feedback:', item.metadata.original_sku);
                                return {
                                  sku: item.metadata.original_sku, // Use original SKU from metadata
                                  description: `Product not found: ${item.metadata.original_sku}`,
                                  quantity: item.quantity,
                                  unit_price: 0, // Original was not found, so price was 0
                                  currency: item.currency,
                                  subtotal: 0,
                                  product_id: null,
                                  metadata: {}
                                };
                              }
                              return undefined;
                            })()}
                            onFeedbackChange={handleItemFeedbackChange}
                            trigger={
                              <Button
                                variant={item.metadata?.item_feedback ? "default" : "outline"}
                                size="icon"
                                title={item.metadata?.item_feedback ? "Edit feedback for this item" : "Provide feedback on this item"}
                              >
                                <MessageSquare className="h-4 w-4" />
                              </Button>
                            }
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeItem(index)}
                            title="Remove item"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    )
                  })}
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

      {/* Product Search Dialog */}
      <ProductSearchDialog
        open={searchDialogOpen}
        onOpenChange={handleDialogClose}
        onSelectProduct={handleProductSelect}
      />
    </div>
  )
}
