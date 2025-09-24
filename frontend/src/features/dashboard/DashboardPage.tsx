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
import { useDashboardStats, useRecentQuotes, useRecentUploads } from './api'
import ItemFeedbackAnalytics from '../quotes/components/ItemFeedbackAnalytics'

export default function DashboardPage() {
  // Fetch real data from APIs
  const { data: stats, isLoading: statsLoading, isError: statsError, error: statsErrorMessage } = useDashboardStats()
  const { data: recentQuotes, isLoading: quotesLoading, isError: quotesError, error: quotesErrorMessage } = useRecentQuotes(5)
  const { data: recentUploads, isLoading: uploadsLoading, isError: uploadsError, error: uploadsErrorMessage } = useRecentUploads(5)

  // Use fallback values if data is loading or error
  const displayStats = stats || { brands: 0, products: 0, quotes: 0, uploads: 0 }
  const displayQuotes = recentQuotes || []
  const displayUploads = recentUploads || []

  // Show error message if any API calls failed
  if (statsError || quotesError || uploadsError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-protect-black">Dashboard</h1>
          <p className="text-protect-medium-grey text-lg">
            Welcome to Protect-IP Quote Generator
          </p>
        </div>
        <Card className="border-protect-error bg-protect-error/5">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="h-4 w-4 bg-protect-error rounded-full"></div>
              <p className="text-protect-error font-medium">
                Failed to load dashboard data. Please try refreshing the page.
              </p>
            </div>
            {(statsErrorMessage || quotesErrorMessage || uploadsErrorMessage) && (
              <p className="text-protect-medium-grey text-sm mt-2">
                Error: {(statsErrorMessage?.message || quotesErrorMessage?.message || uploadsErrorMessage?.message)}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

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
            <div className="text-3xl font-bold text-protect-black mb-1">{statsLoading ? '...' : displayStats.brands.toLocaleString()}</div>
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
            <div className="text-3xl font-bold text-protect-black mb-1">{statsLoading ? '...' : displayStats.products.toLocaleString()}</div>
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
            <div className="text-3xl font-bold text-protect-black mb-1">{statsLoading ? '...' : displayStats.quotes.toLocaleString()}</div>
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
            <div className="text-3xl font-bold text-protect-black mb-1">{statsLoading ? '...' : displayStats.uploads.toLocaleString()}</div>
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
              {quotesLoading ? (
                <div className="p-4 text-center text-protect-medium-grey">
                  Loading recent quotes...
                </div>
              ) : displayQuotes.length === 0 ? (
                <div className="p-4 text-center text-protect-medium-grey">
                  No recent quotes
                </div>
              ) : (
                displayQuotes.map((quote) => (
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
                ))
              )}
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
              {uploadsLoading ? (
                <div className="p-4 text-center text-protect-medium-grey">
                  Loading recent uploads...
                </div>
              ) : displayUploads.length === 0 ? (
                <div className="p-4 text-center text-protect-medium-grey">
                  No recent uploads
                </div>
              ) : (
                displayUploads.map((upload) => (
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
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Item Feedback Analytics */}
      <ItemFeedbackAnalytics />

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
