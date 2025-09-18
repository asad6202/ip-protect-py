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
import { formatCurrency, formatRelativeTime } from '@/lib-utils/format'
import { Quote, ProductUpload } from '@/lib-utils/types'

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
        <h1 className="text-4xl font-bold tracking-tight text-protect-black">Dashboard</h1>
        <p className="text-protect-medium-grey text-lg">
          Welcome to Protect-IP Quote Generator
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-gradient-to-br from-white to-protect-light-grey border-protect-gray-light hover:border-protect-red/40 hover:shadow-protect-red transition-all duration-300 group">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-protect-medium-grey">Brands</CardTitle>
            <Building2 className="h-5 w-5 text-protect-red group-hover:scale-110 transition-transform duration-200" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-protect-black mb-1">{mockStats.brands}</div>
            <p className="text-xs text-protect-medium-grey font-medium">
              Active brands
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-white to-protect-light-grey border-protect-gray-light hover:border-protect-red/40 hover:shadow-protect-red transition-all duration-300 group">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-protect-medium-grey">Products</CardTitle>
            <Package className="h-5 w-5 text-protect-red group-hover:scale-110 transition-transform duration-200" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-protect-black mb-1">{mockStats.products.toLocaleString()}</div>
            <p className="text-xs text-protect-medium-grey font-medium">
              Available products
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-white to-protect-light-grey border-protect-gray-light hover:border-protect-red/40 hover:shadow-protect-red transition-all duration-300 group">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-protect-medium-grey">Quotes</CardTitle>
            <ShoppingCart className="h-5 w-5 text-protect-red group-hover:scale-110 transition-transform duration-200" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-protect-black mb-1">{mockStats.quotes}</div>
            <p className="text-xs text-protect-medium-grey font-medium">
              Generated quotes
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-white to-protect-light-grey border-protect-gray-light hover:border-protect-red/40 hover:shadow-protect-red transition-all duration-300 group">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-protect-medium-grey">Uploads</CardTitle>
            <Upload className="h-5 w-5 text-protect-red group-hover:scale-110 transition-transform duration-200" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-protect-black mb-1">{mockStats.uploads}</div>
            <p className="text-xs text-protect-medium-grey font-medium">
              Product uploads
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Quotes */}
        <Card className="border-protect-gray-light hover:border-protect-red/30 transition-all duration-200">
          <CardHeader className="border-b border-protect-light-grey">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold text-protect-black">Recent Quotes</CardTitle>
              <Button asChild size="sm" className="btn-protect-outline">
                <Link to="/quotes">
                  View all
                </Link>
              </Button>
            </div>
            <CardDescription className="text-protect-medium-grey">
              Latest generated quotes
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-protect-light-grey">
              {mockRecentQuotes.map((quote) => (
                <div key={quote.id} className="flex items-center justify-between p-4 hover:bg-protect-light-grey/50 transition-colors duration-200 group">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none text-protect-black group-hover:text-protect-red transition-colors">
                      {quote.title || 'Untitled Quote'}
                    </p>
                    <p className="text-xs text-protect-medium-grey">
                      {formatRelativeTime(quote.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-protect-black">
                      {formatCurrency(quote.total_amount || 0, quote.currency || 'USD')}
                    </p>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      quote.status === 'draft' ? 'bg-protect-warning/10 text-protect-warning' :
                      quote.status === 'sent' ? 'bg-protect-success/10 text-protect-success' :
                      'bg-protect-medium-grey/10 text-protect-medium-grey'
                    }`}>
                      {quote.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Uploads */}
        <Card className="border-protect-gray-light hover:border-protect-red/30 transition-all duration-200">
          <CardHeader className="border-b border-protect-light-grey">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold text-protect-black">Recent Uploads</CardTitle>
              <Button asChild size="sm" className="btn-protect-outline">
                <Link to="/brands">
                  View all
                </Link>
              </Button>
            </div>
            <CardDescription className="text-protect-medium-grey">
              Latest product uploads
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-protect-light-grey">
              {mockRecentUploads.map((upload) => (
                <div key={upload.id} className="flex items-center justify-between p-4 hover:bg-protect-light-grey/50 transition-colors duration-200 group">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none text-protect-black group-hover:text-protect-red transition-colors">
                      {upload.original_name}
                    </p>
                    <p className="text-xs text-protect-medium-grey">
                      {upload.row_count?.toLocaleString()} rows • {formatRelativeTime(upload.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      upload.status === 'processed' ? 'bg-protect-success/10 text-protect-success' :
                      upload.status === 'processing' ? 'bg-protect-warning/10 text-protect-warning' :
                      'bg-protect-error/10 text-protect-error'
                    }`}>
                      {upload.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="border-protect-gray-light hover:border-protect-red/30 transition-all duration-200">
        <CardHeader className="border-b border-protect-light-grey">
          <CardTitle className="text-lg font-semibold text-protect-black">Quick Actions</CardTitle>
          <CardDescription className="text-protect-medium-grey">
            Get started with common tasks
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button asChild className="bg-protect-red hover:bg-protect-red-dark text-white shadow-protect-red hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 group">
              <Link to="/quotes/new" className="flex items-center justify-center">
                <Plus className="mr-2 h-4 w-4 group-hover:rotate-90 transition-transform duration-200" />
                Generate Quote
              </Link>
            </Button>
            <Button asChild className="btn-protect-outline group">
              <Link to="/brands" className="flex items-center justify-center">
                <Upload className="mr-2 h-4 w-4 group-hover:scale-110 transition-transform duration-200" />
                Upload Products
              </Link>
            </Button>
            <Button asChild className="btn-protect-outline group">
              <Link to="/brands" className="flex items-center justify-center">
                <Building2 className="mr-2 h-4 w-4 group-hover:scale-110 transition-transform duration-200" />
                Manage Brands
              </Link>
            </Button>
            <Button asChild className="btn-protect-outline group">
              <Link to="/rules" className="flex items-center justify-center">
                <Settings className="mr-2 h-4 w-4 group-hover:rotate-90 transition-transform duration-200" />
                Configure Rules
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
