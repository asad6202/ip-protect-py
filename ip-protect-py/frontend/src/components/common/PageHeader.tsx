import { ReactNode } from 'react'
import { Button } from '../ui/button'
import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface PageHeaderProps {
  title: string
  description?: string
  children?: ReactNode
  showBackButton?: boolean
}

export default function PageHeader({ 
  title, 
  description, 
  children, 
  showBackButton = false 
}: PageHeaderProps) {
  const navigate = useNavigate()

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {showBackButton && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(-1)}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
            {description && (
              <p className="text-muted-foreground mt-1">{description}</p>
            )}
          </div>
        </div>
        {children && (
          <div className="flex items-center space-x-2">
            {children}
          </div>
        )}
      </div>
    </div>
  )
}
