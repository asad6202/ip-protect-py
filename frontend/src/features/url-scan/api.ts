/**
 * API functions for URL scanning
 */
import axios from 'axios';

const API_BASE = '/api/v1';

export interface URLScanRequest {
  url: string;
  brand_name?: string;
  auto_ingest?: boolean;
}

export interface URLScanResponse {
  success: boolean;
  url: string;
  products: Array<{
    name: string;
    sku?: string;
    description?: string;
    price?: number;
    category?: string;
    [key: string]: any;
  }>;
  count: number;
  ingested_count?: number;
  error?: string;
}

/**
 * Scan a supplier URL and extract products
 */
export async function scanSupplierURL(request: URLScanRequest): Promise<URLScanResponse> {
  const response = await axios.post(`${API_BASE}/url-scan/scan`, request);
  return response.data;
}
