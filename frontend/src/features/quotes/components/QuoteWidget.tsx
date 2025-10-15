import { Quote } from '@/lib-utils/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Send } from 'lucide-react'

interface QuoteWidgetProps {
  quote: Quote
  onSendQuote?: () => void
}

export default function QuoteWidget({ quote, onSendQuote }: QuoteWidgetProps) {
  const formatCurrency = (amount: number, currency: string = 'CAD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount)
  }

  const statusBadgeConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
    draft: { label: 'DRAFT', variant: 'destructive' },
    pending: { label: 'PENDING', variant: 'secondary' },
    approved: { label: 'APPROVED', variant: 'default' },
    rejected: { label: 'REJECTED', variant: 'outline' },
  }

  const items = quote.items || []
  const currency = quote.currency || 'CAD'
  const subtotal = items.reduce((sum, item) => sum + (item.subtotal || 0), 0)
  
  const taxRate = 0.05
  const taxAmount = subtotal * taxRate
  const grandTotal = subtotal + taxAmount

  const statusConfig = statusBadgeConfig[quote.status] || statusBadgeConfig.draft

  return (
    <Card className="overflow-hidden">
      {/* Header with Logo and Quote ID */}
      <div className="flex items-center justify-between px-6 py-4 bg-white border-b">
        <img
          src="https://www.protect-ip.ca/medias/img/logo-protectip-en.png"
          alt="Protect-IP"
          className="h-10 object-contain"
        />
        <div className="ml-auto">
          <Badge variant="secondary" className="text-xs">
            Quote #{quote.id?.substring(0, 8) || 'N/A'}
          </Badge>
        </div>
      </div>

      {/* Quote Summary Section */}
      {quote.prompt && (
        <div className="px-6 py-4 bg-gray-50 border-b">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Quote Request</h4>
          <p className="text-sm text-gray-900">{quote.prompt}</p>
          {quote.total_amount && (
            <div className="mt-3 flex items-center gap-4">
              <div>
                <span className="text-xs text-gray-500">Estimated Value: </span>
                <span className="text-sm font-semibold text-gray-900">
                  {formatCurrency(quote.total_amount, currency)}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quote Items Header */}
      <div className="flex items-center justify-between px-6 py-3 bg-[#111111] text-white">
        <div>
          <h3 className="font-semibold text-base">Quote items</h3>
          <p className="text-sm text-gray-300">{items.length} items</p>
        </div>
        <Badge variant={statusConfig.variant} className="ml-auto">
          {statusConfig.label}
        </Badge>
      </div>

      {/* Items List */}
      <div className="divide-y">
        {items.map((item, idx) => (
          <div key={item.id || `${item.sku}-${idx}`} className="flex gap-4 items-stretch px-6 py-4 bg-white">
            <div className="flex-1 space-y-1">
              <p className="text-sm font-semibold text-gray-900 line-clamp-2">
                {item.description}
              </p>
              <p className="text-xs text-gray-500">
                SKU: {item.sku}
                {item.metadata?.manufacturer && ` · ${item.metadata.manufacturer}`}
              </p>
              <p className="text-xs text-gray-500">
                Unit: {formatCurrency(item.unit_price || 0, currency)}
              </p>
            </div>
            <div className="min-w-[120px] text-right space-y-1">
              <p className="text-xs text-gray-500">Qty: {item.quantity}</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatCurrency(item.subtotal || 0, currency)}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="border-t border-gray-200" />

      {/* Totals Section */}
      <div className="px-6 py-4 bg-white">
        <div className="flex">
          <div className="flex-1" />
          <div className="min-w-[260px] space-y-3">
            {/* Subtotal */}
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Subtotal</span>
              <span className="text-sm text-gray-900">
                {formatCurrency(subtotal, currency)}
              </span>
            </div>

            {/* Tax */}
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">
                Tax (GST {(taxRate * 100).toFixed(0)}%)
              </span>
              <span className="text-sm text-gray-900">
                {formatCurrency(taxAmount, currency)}
              </span>
            </div>

            {/* Grand Total */}
            <div className="flex justify-between px-4 py-2 bg-[#111111] rounded-lg">
              <span className="text-white font-semibold">Total</span>
              <span className="text-white font-bold text-base">
                {formatCurrency(grandTotal, currency)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Send Quote Button */}
      {onSendQuote && (
        <CardContent className="px-6 py-4 bg-gray-50 border-t">
          <Button 
            onClick={onSendQuote} 
            className="w-full bg-[#111111] hover:bg-[#333333] text-white"
          >
            <Send className="mr-2 h-4 w-4" />
            Send quote
          </Button>
        </CardContent>
      )}
    </Card>
  )
}
