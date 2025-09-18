import { useState } from 'react'
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
  Menu,
  ChevronLeft
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
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="h-screen bg-background">
      {/* Sidebar */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 bg-card border-r transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}>
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center justify-between px-3 border-b">
            {!collapsed && (
              <h1 className="text-xl font-bold ml-3">IP Protect</h1>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCollapsed(!collapsed)}
              className="ml-auto"
            >
              {collapsed ? (
                <Menu className="h-5 w-5" />
              ) : (
                <ChevronLeft className="h-5 w-5" />
              )}
            </Button>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href || 
                (item.href !== '/' && location.pathname.startsWith(item.href))
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    'group relative',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                  title={collapsed ? item.name : undefined}
                >
                  <item.icon className={cn(
                    "h-5 w-5 flex-shrink-0",
                    collapsed ? "mx-auto" : "mr-3"
                  )} />
                  {!collapsed && (
                    <span className="transition-opacity duration-300">
                      {item.name}
                    </span>
                  )}
                  {collapsed && (
                    <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground rounded-md text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50 whitespace-nowrap border shadow-md">
                      {item.name}
                    </div>
                  )}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className={cn(
        "transition-all duration-300 ease-in-out h-full flex flex-col",
        collapsed ? "pl-16" : "pl-64"
      )}>
        <main className="flex-1 py-4 overflow-y-auto">
          <div className="mx-auto max-w-full px-4 sm:px-6 lg:px-8 min-h-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
