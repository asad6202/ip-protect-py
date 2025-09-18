import { useParams, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table'
import { Package, ExternalLink } from 'lucide-react'
import PageHeader from '@/components/common/PageHeader'
import EmptyState from '@/components/common/EmptyState'
import { useGetProduct } from '../api'
import { useGetBrand } from '../../brands/api'
import { formatCurrency, formatDateTime } from '@/lib/format'

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: product, isLoading, error } = useGetProduct(id!)
  const { data: brand } = useGetBrand(product?.brand_id || '')

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Loading..." 
          description=""
          showBackButton
        />
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="animate-pulse">
            <CardHeader>
              <div className="h-6 bg-muted rounded w-1/2"></div>
              <div className="h-4 bg-muted rounded w-1/3"></div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="h-4 bg-muted rounded"></div>
                <div className="h-4 bg-muted rounded w-2/3"></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Product Not Found" 
          description=""
          showBackButton
        />
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Package className="h-12 w-12" />}
              title="Product not found"
              description="The product you're looking for doesn't exist or has been deleted."
              action={{
                label: 'Back to Products',
                onClick: () => window.history.back()
              }}
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title={product.sku}
        description={product.description}
        showBackButton
        children={
          <Button asChild variant="outline">
            <Link to={`/products?search=${product.sku}`}>
              <ExternalLink className="mr-2 h-4 w-4" />
              Find Similar
            </Link>
          </Button>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Product details and specifications
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">SKU</label>
                <p className="font-mono text-sm">{product.sku}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Status</label>
                <p className="text-sm">
                  <Badge variant="outline">{product.status}</Badge>
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Price</label>
                <p className="text-lg font-semibold">
                  {formatCurrency(product.price, product.currency)}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Family</label>
                <p className="text-sm">
                  <Badge variant="outline">{product.family}</Badge>
                </p>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">Description</label>
              <p className="text-sm">{product.description}</p>
            </div>

            {brand && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">Brand</label>
                <p className="text-sm">
                  <Button asChild variant="link" className="p-0 h-auto">
                    <Link to={`/brands/${brand.id}`}>
                      {brand.name}
                    </Link>
                  </Button>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Technical Specifications */}
        <Card>
          <CardHeader>
            <CardTitle>Technical Specifications</CardTitle>
            <CardDescription>
              Hardware and feature specifications
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">Form Factor</TableCell>
                  <TableCell>{product.form_factor || 'N/A'}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Outdoor</TableCell>
                  <TableCell>
                    <Badge variant={product.outdoor ? 'default' : 'outline'}>
                      {product.outdoor ? 'Yes' : 'No'}
                    </Badge>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">PoE</TableCell>
                  <TableCell>
                    <Badge variant={product.poe ? 'default' : 'outline'}>
                      {product.poe ? 'Yes' : 'No'}
                    </Badge>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">PoE+</TableCell>
                  <TableCell>
                    <Badge variant={product.poe_plus ? 'default' : 'outline'}>
                      {product.poe_plus ? 'Yes' : 'No'}
                    </Badge>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">IR Range</TableCell>
                  <TableCell>{product.ir_range_m ? `${product.ir_range_m}m` : 'N/A'}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Resolution</TableCell>
                  <TableCell>{product.resolution_mp ? `${product.resolution_mp}MP` : 'N/A'}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Vandal IK10</TableCell>
                  <TableCell>
                    <Badge variant={product.vandal_ik10 ? 'default' : 'outline'}>
                      {product.vandal_ik10 ? 'Yes' : 'No'}
                    </Badge>
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">NVR Channels</TableCell>
                  <TableCell>{product.nvr_channels || 'N/A'}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Switch Ports</TableCell>
                  <TableCell>{product.switch_ports || 'N/A'}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Accessory Type</TableCell>
                  <TableCell>{product.accessory_type || 'N/A'}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Metadata</CardTitle>
          <CardDescription>
            System information and timestamps
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label className="font-medium text-muted-foreground">Created</label>
              <p>{formatDateTime(product.created_at)}</p>
            </div>
            <div>
              <label className="font-medium text-muted-foreground">Last Updated</label>
              <p>{formatDateTime(product.updated_at)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
