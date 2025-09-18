import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'
import { 
  Package, 
  Building2, 
  ShoppingCart, 
  Upload, 
  Plus,
  Settings
} from 'lucide-react'
import { formatCurrency, formatRelativeTime } from '@/lib/format'
import { Quote, ProductUpload } from '@/lib/types'

// Mock data for now - replace with actual API calls
const mockStats = {
  brands: 3,
  products: 1247,
  quotes: 23,
  uploads: 8
}

const mockRecentQuotes: Quote[] = [
  {
    id: '1',
    title: 'Security System Quote',
    prompt: 'Need a complete security system for office building',
    currency: 'USD',
    total_amount: 15420.50,
    status: 'draft',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: '2',
    title: 'Retail Store Cameras',
    prompt: 'IP cameras for retail store with night vision',
    currency: 'USD',
    total_amount: 8750.00,
    status: 'sent',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString()
  }
]

const mockRecentUploads: ProductUpload[] = [
  {
    id: '1',
    brand_id: '1',
    original_name: 'axis_products.csv',
    stored_path: '/uploads/axis_products.csv',
    row_count: 450,
    status: 'processed',
    created_at: new Date().toISOString()
  },
  {
    id: '2',
    brand_id: '2',
    original_name: 'hanwha_products.csv',
    stored_path: '/uploads/hanwha_products.csv',
    row_count: 320,
    status: 'processing',
    created_at: new Date(Date.now() - 3600000).toISOString()
  }
]

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to IP Protect Quote Generator
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Brands</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.brands}</div>
            <p className="text-xs text-muted-foreground">
              Active brands
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.products.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Available products
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Quotes</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.quotes}</div>
            <p className="text-xs text-muted-foreground">
              Generated quotes
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Uploads</CardTitle>
            <Upload className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.uploads}</div>
            <p className="text-xs text-muted-foreground">
              Product uploads
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Quotes */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Quotes</CardTitle>
              <Button asChild variant="outline" size="sm">
                <Link to="/quotes">
                  View all
                </Link>
              </Button>
            </div>
            <CardDescription>
              Latest generated quotes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockRecentQuotes.map((quote) => (
                <div key={quote.id} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {quote.title || 'Untitled Quote'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatRelativeTime(quote.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {formatCurrency(quote.total_amount || 0, quote.currency || 'USD')}
                    </p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {quote.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Uploads */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Uploads</CardTitle>
              <Button asChild variant="outline" size="sm">
                <Link to="/uploads">
                  View all
                </Link>
              </Button>
            </div>
            <CardDescription>
              Latest product uploads
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockRecentUploads.map((upload) => (
                <div key={upload.id} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {upload.original_name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {upload.row_count?.toLocaleString()} rows • {formatRelativeTime(upload.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground capitalize">
                      {upload.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Get started with common tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button asChild>
              <Link to="/quotes/new">
                <Plus className="mr-2 h-4 w-4" />
                Generate Quote
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/uploads">
                <Upload className="mr-2 h-4 w-4" />
                Upload Products
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/brands">
                <Building2 className="mr-2 h-4 w-4" />
                Manage Brands
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/rules">
                <Settings className="mr-2 h-4 w-4" />
                Configure Rules
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
