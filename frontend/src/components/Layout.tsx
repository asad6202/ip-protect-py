import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { Button } from './ui/button'
import Logo from './Logo'
import { 
  Home, 
  Package, 
  ShoppingCart, 
  Building2, 
  Settings, 
  FileText,
  Menu,
  ChevronLeft
} from 'lucide-react'
import { cn } from '@/lib-utils/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Quotes', href: '/quotes', icon: ShoppingCart },
  { name: 'Products', href: '/products', icon: Package },
  { name: 'Brands', href: '/brands', icon: Building2 },
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
        "fixed inset-y-0 left-0 z-50 bg-protect-white border-r border-protect-gray-light transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}>
        <div className="flex h-full flex-col">
          <div className={cn(
            "flex h-16 items-center border-b border-protect-gray-light",
            collapsed ? "justify-center px-2" : "justify-between px-3"
          )}>
            {!collapsed && (
              <Logo size="md" />
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCollapsed(!collapsed)}
              className={cn(
                "text-protect-black hover:bg-protect-red hover:text-protect-white",
                collapsed ? "ml-0" : "ml-auto"
              )}
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
                    'flex items-center text-sm font-medium rounded-md transition-colors group relative',
                    collapsed ? 'justify-center px-2 py-2' : 'px-3 py-2',
                    isActive
                      ? 'bg-protect-red text-protect-white'
                      : 'text-protect-black hover:bg-protect-red hover:text-protect-white'
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
                    <div className="absolute left-full ml-2 px-2 py-1 bg-protect-black text-protect-white rounded-md text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50 whitespace-nowrap border border-protect-gray-light shadow-md">
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
        <main className="flex-1 py-4 h-full overflow-y-auto">
          <div className="mx-auto max-w-full px-4 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
