import { useState } from "react";
import { Link } from "react-router-dom";
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
import { formatCurrency } from "@/lib/format";

export default function ProductListPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [selectedFamily, setSelectedFamily] = useState("all");
  const [selectedBrand, setSelectedBrand] = useState("all");
  const [accessoryFilter, setAccessoryFilter] = useState<string>("all");

  const filters = {
    page,
    page_size: 20,
    ...(search && { search }),
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
      <div className="space-y-2">
        <div className="pb-2">
          <h1 className="text-2xl font-bold text-foreground">Products</h1>
          <p className="text-sm text-muted-foreground">
            Browse and search products
          </p>
        </div>
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-48"></div>
                    <div className="h-3 bg-muted rounded w-32"></div>
                  </div>
                  <div className="h-6 bg-muted rounded w-20"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <div className="pb-2">
          <h1 className="text-2xl font-bold text-foreground">Products</h1>
          <p className="text-sm text-muted-foreground">
            Browse and search products
          </p>
        </div>
        <Card>
          <CardContent className="py-12">
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
    );
  }

  const products = productsData?.items || [];
  const totalPages = productsData?.pages || 1;

  return (
    <div className="space-y-2">
      <div className="pb-2">
        <h1 className="text-2xl font-bold text-foreground">Products</h1>
        <p className="text-sm text-muted-foreground">
          Browse and search products
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
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
            {(search ||
              selectedFamily !== "all" ||
              selectedBrand !== "all" ||
              accessoryFilter !== "all") && (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                <X className="mr-2 h-4 w-4" />
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {products.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={<Package className="h-12 w-12" />}
              title="No products found"
              description="Try adjusting your search criteria or upload some products."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Table Container */}
          <Card className="shadow-sm border-border/50">
            <CardContent className="p-0">
              {/* Table Header - Fixed */}
              <div className="border-b border-border/50 bg-background">
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

              {/* Table Body - Scrollable with fixed height */}
              <div className="max-h-[600px] overflow-y-auto">
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
                            variant="outline"
                            size="sm"
                            className="h-8 text-xs"
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

          {/* Pagination - Positioned below table */}
          {totalPages > 1 && (
            <Card className="shadow-sm border-border/50">
              <CardContent className="py-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Showing {(page - 1) * 20 + 1} to{" "}
                    {Math.min(page * 20, productsData?.total || 0)} of{" "}
                    {productsData?.total || 0} products
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="h-8"
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
                            className="h-8 w-8 p-0"
                          >
                            {pageNum}
                          </Button>
                        );
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page === totalPages}
                      className="h-8"
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
  );
}
