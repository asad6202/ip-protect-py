import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  BarChart3,
  Target
} from 'lucide-react'
import { useGetItemFeedbackAnalytics } from '../api-item-feedback'

export default function ItemFeedbackAnalytics() {
  const { data: analytics, isLoading, error } = useGetItemFeedbackAnalytics()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded w-1/2"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error || !analytics) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            Failed to load analytics data
          </div>
        </CardContent>
      </Card>
    )
  }

  const { feedback_type_distribution, problematic_skus, correction_patterns, recent_trends } = analytics

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Feedback</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {feedback_type_distribution.reduce((sum: number, item: any) => sum + item.count, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Item-level feedback entries
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Positive Feedback</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {feedback_type_distribution.find((item: any) => item.feedback_type === 'correct')?.count || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Correct item selections
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Issues Found</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {feedback_type_distribution
                .filter((item: any) => item.feedback_type !== 'correct')
                .reduce((sum: number, item: any) => sum + item.count, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Items needing attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Problematic SKUs</CardTitle>
            <Target className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {problematic_skus.length}
            </div>
            <p className="text-xs text-muted-foreground">
              SKUs with multiple issues
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Feedback Type Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Feedback Type Distribution</CardTitle>
          <CardDescription>
            Breakdown of feedback types provided by users
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {feedback_type_distribution.map((item: any) => {
              const total = feedback_type_distribution.reduce((sum: number, i: any) => sum + i.count, 0)
              const percentage = (item.count / total) * 100
              
              const typeConfig = {
                correct: { color: 'bg-green-100 text-green-800', icon: CheckCircle },
                incorrect: { color: 'bg-red-100 text-red-800', icon: XCircle },
                missing: { color: 'bg-orange-100 text-orange-800', icon: AlertTriangle },
                wrong_quantity: { color: 'bg-blue-100 text-blue-800', icon: TrendingUp },
                wrong_price: { color: 'bg-purple-100 text-purple-800', icon: TrendingDown },
                wrong_specs: { color: 'bg-gray-100 text-gray-800', icon: Target }
              }
              
              const config = typeConfig[item.feedback_type as keyof typeof typeConfig] || typeConfig.wrong_specs
              const Icon = config.icon
              
              return (
                <div key={item.feedback_type} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span className="font-medium capitalize">
                        {item.feedback_type.replace('_', ' ')}
                      </span>
                      <Badge className={config.color}>
                        {item.count}
                      </Badge>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {percentage.toFixed(1)}%
                    </span>
                  </div>
                  <Progress value={percentage} className="h-2" />
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Problematic SKUs */}
      <Card>
        <CardHeader>
          <CardTitle>Most Problematic SKUs</CardTitle>
          <CardDescription>
            SKUs that have received the most negative feedback
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {problematic_skus.slice(0, 10).map((sku: any) => (
              <div key={sku.sku} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-1">
                  <div className="font-mono text-sm font-medium">{sku.sku}</div>
                  <div className="text-sm text-muted-foreground line-clamp-2">
                    {sku.description}
                  </div>
                  <div className="flex gap-2">
                    {sku.feedback_types.map((type: string) => (
                      <Badge key={type} variant="outline" className="text-xs">
                        {type.replace('_', ' ')}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-red-600">
                    {sku.feedback_count}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    issues
                  </div>
                  {sku.avg_rating && (
                    <div className="text-xs text-muted-foreground">
                      Avg: {sku.avg_rating.toFixed(1)}⭐
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Correction Patterns */}
      <Card>
        <CardHeader>
          <CardTitle>Common Correction Patterns</CardTitle>
          <CardDescription>
            Most frequent types of corrections requested
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {correction_patterns.slice(0, 8).map((pattern: any) => (
              <div key={`${pattern.field}-${pattern.reason}`} className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="font-medium capitalize">
                    {pattern.field?.replace('_', ' ')}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {pattern.reason}
                  </div>
                </div>
                <Badge variant="outline">
                  {pattern.count} times
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Trends */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Feedback Trends</CardTitle>
          <CardDescription>
            Feedback activity over the last 30 days
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {recent_trends.slice(0, 10).map((trend: any) => (
              <div key={`${trend.date}-${trend.feedback_type}`} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">{trend.date}</span>
                  <Badge variant="outline" className="text-xs">
                    {trend.feedback_type.replace('_', ' ')}
                  </Badge>
                </div>
                <span className="font-medium">{trend.count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
