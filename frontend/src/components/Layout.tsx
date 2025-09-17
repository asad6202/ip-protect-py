import { Outlet, Link, useLocation } from 'react-router-dom'
import { Button } from './ui/button'
import { 
  Home, 
  Package, 
  Upload, 
  ShoppingCart, 
  Building2, 
  Settings, 
  FileText,
  BarChart3
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Quotes', href: '/quotes', icon: ShoppingCart },
  { name: 'Products', href: '/products', icon: Package },
  { name: 'Brands', href: '/brands', icon: Building2 },
  { name: 'Uploads', href: '/uploads', icon: Upload },
  { name: 'Rules', href: '/rules', icon: Settings },
  { name: 'Prompts', href: '/prompts', icon: FileText },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-card border-r">
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center px-6 border-b">
            <h1 className="text-xl font-bold">IP Protect</h1>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href || 
                (item.href !== '/' && location.pathname.startsWith(item.href))
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="py-6">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
