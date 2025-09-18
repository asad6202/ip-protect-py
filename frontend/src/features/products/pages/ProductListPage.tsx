import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Package, Eye, Search, X } from "lucide-react";
import EmptyState from "@/components/common/EmptyState";
import { useListProducts, useProductFamilies } from "../api";
import { useListBrands } from "@/features/brands/api";
import { formatCurrency } from "@/lib-utils/format";

export default function ProductListPage() {
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [selectedFamily, setSelectedFamily] = useState("all");
  const [selectedBrand, setSelectedBrand] = useState("all");
  const [accessoryFilter, setAccessoryFilter] = useState<string>("all");

  // Handle URL parameters
  useEffect(() => {
    const brandParam = searchParams.get('brand_id') || searchParams.get('brand');
    if (brandParam) {
      setSelectedBrand(brandParam);
    }
  }, [searchParams]);

  const trimmedSearch = search.trim();
  
  const filters = {
    page,
    page_size: 20,
    ...(trimmedSearch && { search: trimmedSearch }),
    ...(selectedFamily !== "all" && { family: selectedFamily }),
    ...(selectedBrand !== "all" && { brand_id: selectedBrand }),
    ...(accessoryFilter !== "all" && {
      is_accessory: accessoryFilter === "true",
    }),
  };

  const { data: productsData, isLoading, error } = useListProducts(filters);
  const { data: brands } = useListBrands();
  const { data: families } = useProductFamilies();

  // Reset page when filters change
  const handleFilterChange = (newFilters: any) => {
    setPage(1);
    return newFilters;
  };

  const clearFilters = () => {
    setSearch("");
    setSelectedFamily("all");
    setSelectedBrand("all");
    setAccessoryFilter("all");
    setPage(1);
  };

  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        {/* Fixed Header */}
        <div className="flex-shrink-0 space-y-6">
          <div className="pb-2">
            <h1 className="text-2xl font-bold text-foreground">Products</h1>
            <p className="text-sm text-muted-foreground">
              Browse and search products
            </p>
          </div>
        </div>

        {/* Fixed Filters */}
        <Card className="mb-6 flex-shrink-0">
          <CardContent className="p-4">
            <div className="flex flex-col space-y-4 lg:flex-row lg:space-y-0 lg:space-x-4">
              <div className="relative flex-1">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
              <div className="w-full lg:w-48">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
              <div className="w-full lg:w-48">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
              <div className="w-full lg:w-48">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scrollable Loading State */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <Card className="h-full">
            <CardContent className="p-0 h-full flex flex-col">
              <div className="border-b border-border/50 bg-background flex-shrink-0 sticky top-0 z-10">
                <div className="h-12 bg-muted animate-pulse"></div>
              </div>
              <div className="flex-1 overflow-y-auto max-h-[calc(100vh-400px)] sm:max-h-[calc(100vh-350px)] lg:max-h-[calc(100vh-300px)]">
                <div className="space-y-0">
                  {[...Array(10)].map((_, i) => (
                    <div key={i} className="h-16 border-b border-border/30 bg-muted/10 animate-pulse"></div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col">
        {/* Fixed Header */}
        <div className="flex-shrink-0 space-y-6">
          <div className="pb-2">
            <h1 className="text-2xl font-bold text-foreground">Products</h1>
            <p className="text-sm text-muted-foreground">
              Browse and search products
            </p>
          </div>
        </div>

        {/* Fixed Filters */}
        <Card className="mb-6 flex-shrink-0">
          <CardContent className="p-4">
            <div className="flex flex-col space-y-4 lg:flex-row lg:space-y-0 lg:space-x-4">
              <div className="relative flex-1">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
              <div className="w-full lg:w-48">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
              <div className="w-full lg:w-48">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
              <div className="w-full lg:w-48">
                <div className="h-10 bg-muted rounded animate-pulse"></div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scrollable Error State */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <Card className="h-full">
            <CardContent className="py-12 h-full flex items-center justify-center">
              <EmptyState
                icon={<Package className="h-12 w-12" />}
                title="Error loading products"
                description="There was an error loading the products. Please try again."
                action={{
                  label: "Retry",
                  onClick: () => window.location.reload(),
                }}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const products = productsData?.items || [];
  const totalPages = productsData?.pages || 1;

  return (
    <div className="h-full flex flex-col">
      {/* Fixed Header */}
      <div className="flex-shrink-0 space-y-6">
        <div className="pb-2">
          <h1 className="text-2xl font-bold text-foreground">Products</h1>
          <p className="text-sm text-muted-foreground">
            Browse and search products
            {selectedBrand !== "all" && brands && (
              <span className="ml-2">
                • Filtered by brand: <span className="font-medium text-primary">
                  {brands.find(b => b.id === selectedBrand)?.name || selectedBrand}
                </span>
              </span>
            )}
          </p>
        </div>

        {/* Fixed Filters */}
        <Card className="mb-8 flex-shrink-0">
          <CardContent className="p-4">
            <div className="flex flex-col space-y-4 lg:flex-row lg:space-y-0 lg:space-x-4">
              {/* Search */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search products..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    handleFilterChange({});
                  }}
                  className="pl-10"
                />
              </div>

              {/* Family Filter */}
              <div className="w-full lg:w-48">
                <Select
                  value={selectedFamily}
                  onValueChange={(value) => {
                    setSelectedFamily(value);
                    handleFilterChange({});
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All families" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All families</SelectItem>
                    {families?.map((family) => (
                      <SelectItem key={family} value={family}>
                        {family}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Brand Filter */}
              <div className="w-full lg:w-48">
                <Select
                  value={selectedBrand}
                  onValueChange={(value) => {
                    setSelectedBrand(value);
                    handleFilterChange({});
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All brands" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All brands</SelectItem>
                    {brands?.map((brand) => (
                      <SelectItem key={brand.id} value={brand.id}>
                        {brand.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Accessory Filter */}
              <div className="w-full lg:w-48">
                <Select
                  value={accessoryFilter}
                  onValueChange={(value) => {
                    setAccessoryFilter(value);
                    handleFilterChange({});
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All products" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All products</SelectItem>
                    <SelectItem value="false">Products only</SelectItem>
                    <SelectItem value="true">Accessories only</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Clear Filters */}
              {(trimmedSearch ||
                selectedFamily !== "all" ||
                selectedBrand !== "all" ||
                accessoryFilter !== "all") && (
                <Button size="sm" className="btn-protect-outline" onClick={clearFilters}>
                  <X className="mr-2 h-4 w-4" />
                  Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Scrollable Content Area with responsive height */}
      <div className="flex-1 min-h-0 overflow-hidden mt-3">
        {products.length === 0 ? (
          <Card className="h-full">
            <CardContent className="py-12 h-full flex items-center justify-center">
              <EmptyState
                icon={<Package className="h-12 w-12" />}
                title="No products found"
                description="Try adjusting your search criteria or upload some products."
              />
            </CardContent>
          </Card>
        ) : (
          <div className="h-full flex flex-col">
            {/* Table Container with Scrollable Body */}
            <Card className="shadow-sm border-border/50 flex-1 min-h-0 overflow-hidden">
              <CardContent className="p-0 h-full flex flex-col">
                {/* Table Header - Fixed */}
                <div className="border-b border-border/50 bg-background flex-shrink-0 sticky top-0 z-10">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="font-semibold text-foreground h-12">
                          SKU
                        </TableHead>
                        <TableHead className="font-semibold text-foreground h-12">
                          Description
                        </TableHead>
                        <TableHead className="font-semibold text-foreground h-12">
                          Family
                        </TableHead>
                        <TableHead className="font-semibold text-foreground h-12">
                          Price
                        </TableHead>
                        <TableHead className="font-semibold text-foreground h-12">
                          Status
                        </TableHead>
                        <TableHead className="text-right font-semibold text-foreground h-12">
                          Actions
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                  </Table>
                </div>

                {/* Table Body - Scrollable with responsive height */}
                <div className="flex-1 overflow-y-auto max-h-[calc(100vh-400px)] sm:max-h-[calc(100vh-350px)] lg:max-h-[calc(100vh-300px)]">
                  <Table>
                    <TableBody>
                      {products.map((product, index) => (
                        <TableRow
                          key={product.id}
                          className={`hover:bg-muted/30 transition-colors duration-200 border-b border-border/30 ${
                            index % 2 === 0 ? "bg-background" : "bg-muted/10"
                          }`}
                        >
                          <TableCell className="font-semibold text-sm py-3">
                            {product.sku}
                          </TableCell>
                          <TableCell className="max-w-md py-3">
                            <span
                              title={product.description}
                              className="cursor-help text-sm text-muted-foreground"
                            >
                              {product.description.length > 60
                                ? `${product.description.substring(0, 60)}...`
                                : product.description}
                            </span>
                          </TableCell>
                          <TableCell className="py-3">
                            <Badge
                              variant="outline"
                              className="text-xs font-medium"
                            >
                              {product.family}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-semibold text-sm py-3">
                            {formatCurrency(product.price, product.currency)}
                          </TableCell>
                          <TableCell className="py-3">
                            <Badge
                              variant={
                                product.status === "active"
                                  ? "default"
                                  : "secondary"
                              }
                              className="text-xs font-medium"
                            >
                              {product.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right py-3">
                            <Button
                              asChild
                              size="sm"
                              className="h-8 text-xs btn-protect-outline"
                            >
                              <Link to={`/products/${product.id}`}>
                                <Eye className="mr-1.5 h-3.5 w-3.5" />
                                View
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            {/* Fixed Pagination */}
            {totalPages > 1 && (
              <Card className="shadow-sm border-border/50 mt-4 flex-shrink-0">
                <CardContent className="py-3">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                      Showing {(page - 1) * 20 + 1} to{" "}
                      {Math.min(page * 20, productsData?.total || 0)} of{" "}
                      {productsData?.total || 0} products
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        onClick={() => setPage(Math.max(1, page - 1))}
                        disabled={page === 1}
                        className="h-8 btn-protect-outline"
                      >
                        Previous
                      </Button>
                      <div className="flex items-center space-x-1">
                        {[...Array(Math.min(5, totalPages))].map((_, i) => {
                          const pageNum =
                            Math.max(1, Math.min(totalPages - 4, page - 2)) + i;
                          if (pageNum > totalPages) return null;
                          return (
                            <Button
                              key={pageNum}
                              variant={pageNum === page ? "default" : "outline"}
                              size="sm"
                              onClick={() => setPage(pageNum)}
                              className={`h-8 w-8 p-0 ${pageNum === page ? "bg-protect-red text-white hover:bg-protect-red-dark" : "btn-protect-outline"}`}
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>
                      <Button
                        size="sm"
                        onClick={() => setPage(Math.min(totalPages, page + 1))}
                        disabled={page === totalPages}
                        className="h-8 btn-protect-outline"
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
