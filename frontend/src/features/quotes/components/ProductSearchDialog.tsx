import { useState, useEffect } from 'react'
import { Search, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useListProducts } from '@/features/products/api'
import { Product } from '@/lib-utils/types'
import { formatCurrency } from '@/lib-utils/format'

interface ProductSearchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectProduct: (product: Product) => void
}

export default function ProductSearchDialog({
  open,
  onOpenChange,
  onSelectProduct
}: ProductSearchDialogProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)

  // Search products with the search term
  const { data: productsData, isLoading } = useListProducts({
    search: searchTerm,
    page_size: 20
  })

  const products = productsData?.items || []

  // Reset selected product when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSelectedProduct(null)
      setSearchTerm('')
    }
  }, [open])

  const handleSelectProduct = () => {
    console.log('Add to Quote clicked, selectedProduct:', selectedProduct)
    if (selectedProduct) {
      console.log('Calling onSelectProduct with:', selectedProduct)
      onSelectProduct(selectedProduct)
      onOpenChange(false)
    } else {
      console.log('No product selected!')
    }
  }

  const handleProductClick = (product: Product) => {
    setSelectedProduct(product)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Search Products</DialogTitle>
          <DialogDescription>
            Search for products by SKU or description to add to your quote
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 flex-1 overflow-hidden flex flex-col">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by SKU or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Results */}
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">Searching products...</div>
              </div>
            ) : products.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">
                  {searchTerm ? 'No products found matching your search' : 'Enter a search term to find products'}
                </div>
              </div>
            ) : (
              <div className="overflow-auto max-h-96">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12"></TableHead>
                      <TableHead>SKU</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Family</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {products.map((product) => (
                      <TableRow
                        key={product.id}
                        className={`cursor-pointer hover:bg-muted/50 ${
                          selectedProduct?.id === product.id ? 'bg-muted' : ''
                        }`}
                        onClick={() => handleProductClick(product)}
                      >
                        <TableCell>
                          {selectedProduct?.id === product.id && (
                            <Check className="h-4 w-4 text-primary" />
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {product.sku}
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="font-medium">{product.description}</div>
                            <div className="flex flex-wrap gap-1">
                              {product.is_accessory && (
                                <Badge variant="secondary" className="text-xs">
                                  Accessory
                                </Badge>
                              )}
                              {product.outdoor && (
                                <Badge variant="outline" className="text-xs">
                                  Outdoor
                                </Badge>
                              )}
                              {product.poe && (
                                <Badge variant="outline" className="text-xs">
                                  PoE
                                </Badge>
                              )}
                              {product.resolution_mp && (
                                <Badge variant="outline" className="text-xs">
                                  {product.resolution_mp}MP
                                </Badge>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {product.family}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(product.price, product.currency)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          {/* Selected Product Summary */}
          {selectedProduct && (
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{selectedProduct.sku}</div>
                    <div className="text-sm text-muted-foreground">
                      {selectedProduct.description}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">
                      {formatCurrency(selectedProduct.price, selectedProduct.currency)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {selectedProduct.family}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-2 pt-4 border-t">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSelectProduct}
              disabled={!selectedProduct}
            >
              Add to Quote
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}