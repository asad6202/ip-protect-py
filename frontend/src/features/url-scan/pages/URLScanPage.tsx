/**
 * URL Scanning page for ingesting products from supplier websites
 */
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { scanSupplierURL, type URLScanRequest, type URLScanResponse } from '../api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react';

export default function URLScanPage() {
  const [url, setUrl] = useState('');
  const [brandName, setBrandName] = useState('');
  const [autoIngest, setAutoIngest] = useState(true);
  const [scanResult, setScanResult] = useState<URLScanResponse | null>(null);

  const scanMutation = useMutation({
    mutationFn: (request: URLScanRequest) => scanSupplierURL(request),
    onSuccess: (data) => {
      setScanResult(data);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setScanResult(null);
    scanMutation.mutate({
      url,
      brand_name: brandName || undefined,
      auto_ingest: autoIngest,
    });
  };

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">URL Product Scanner</h1>
        <p className="text-muted-foreground">
          Scan supplier websites to extract and import product information into your catalog
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Scan Supplier URL</CardTitle>
          <CardDescription>
            Enter a supplier website URL to extract product listings. Products will be automatically added to your database.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="url">Supplier URL *</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://example.com/products"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                disabled={scanMutation.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="brand">Brand Name (optional)</Label>
              <Input
                id="brand"
                type="text"
                placeholder="e.g., Axis, Hanwha, I-Pro"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                disabled={scanMutation.isPending}
              />
              <p className="text-sm text-muted-foreground">
                If provided, products will be associated with this brand
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="auto-ingest"
                checked={autoIngest}
                onChange={(e) => setAutoIngest(e.target.checked)}
                disabled={scanMutation.isPending}
                className="h-4 w-4 rounded border-gray-300"
              />
              <Label htmlFor="auto-ingest" className="text-sm font-normal cursor-pointer">
                Automatically save products to database
              </Label>
            </div>

            <Button
              type="submit"
              disabled={scanMutation.isPending || !url}
              className="w-full"
            >
              {scanMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Scanning URL...
                </>
              ) : (
                <>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Scan URL
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {scanMutation.isError && (
        <div className="mb-6 p-4 border border-red-300 bg-red-50 rounded-lg flex items-start gap-2 text-red-800">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <div>
            <div className="font-medium mb-1">Error scanning URL</div>
            <div className="text-sm">
              {(() => {
                const error = scanMutation.error as any;
                return error?.response?.data?.detail || error?.message || 'Failed to scan URL. Please check the URL and try again.';
              })()}
            </div>
          </div>
        </div>
      )}

      {scanResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Scan Complete
            </CardTitle>
            <CardDescription>
              Found {scanResult.count} product{scanResult.count !== 1 ? 's' : ''} from {scanResult.url}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {scanResult.ingested_count !== undefined && (
              <div className="p-4 border border-green-300 bg-green-50 rounded-lg flex items-start gap-2 text-green-800">
                <CheckCircle2 className="h-5 w-5 mt-0.5 flex-shrink-0" />
                <div>
                  Successfully imported {scanResult.ingested_count} product{scanResult.ingested_count !== 1 ? 's' : ''} into the database
                </div>
              </div>
            )}

            {scanResult.error && (
              <div className="p-4 border border-yellow-300 bg-yellow-50 rounded-lg flex items-start gap-2 text-yellow-800">
                <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="font-medium mb-1">Partial ingestion failure</div>
                  <div className="text-sm">{scanResult.error}</div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              <h3 className="font-semibold">Extracted Products:</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {scanResult.products.map((product, index) => (
                  <div
                    key={index}
                    className="border rounded-lg p-3 bg-muted/50"
                  >
                    <div className="font-medium">{product.name}</div>
                    {product.sku && (
                      <div className="text-sm text-muted-foreground">SKU: {product.sku}</div>
                    )}
                    {product.description && (
                      <div className="text-sm mt-1">{product.description}</div>
                    )}
                    {product.price && (
                      <div className="text-sm font-medium mt-1">${product.price.toFixed(2)}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
