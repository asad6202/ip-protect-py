"""
URL Scanner service for extracting product information from external websites.
"""

import os
import json
import socket
import requests
import ipaddress
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from openai import AsyncOpenAI


class URLScannerService:
    """Service for scanning URLs and extracting product information."""
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    async def scan_url(self, url: str) -> Dict[str, Any]:
        """
        Scan a URL and extract product information.
        
        Args:
            url: URL to scan for product information
        
        Returns:
            Dict with extracted products and metadata
        """
        try:
            # Validate URL for security
            if not self._validate_url(url):
                raise ValueError("Invalid or unsafe URL. Only public HTTP/HTTPS URLs are allowed.")
            
            html_content = self._fetch_url(url)
            if not html_content:
                raise ValueError(f"Failed to fetch content from URL: {url}")
            
            cleaned_text = self._extract_text_from_html(html_content)
            
            products = await self._extract_products_with_ai(url, cleaned_text, html_content)
            
            return {
                "success": True,
                "url": url,
                "products": products,
                "count": len(products)
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "products": [],
                "count": 0
            }
    
    def _validate_url(self, url: str) -> bool:
        """
        Validate URL to prevent SSRF attacks (IPv4 and IPv6).
        
        Args:
            url: URL to validate
        
        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Only allow HTTP and HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Require a hostname
            if not parsed.hostname:
                return False
            
            hostname = parsed.hostname.lower()
            
            # Check if hostname is an IP literal (IPv4 or IPv6)
            try:
                ip_obj = ipaddress.ip_address(hostname)
                
                # Check for IPv4-mapped IPv6 addresses (::ffff:x.x.x.x)
                if isinstance(ip_obj, ipaddress.IPv6Address):
                    # Check for IPv4-mapped addresses
                    if ip_obj.ipv4_mapped:
                        mapped_ipv4 = ip_obj.ipv4_mapped
                        if (mapped_ipv4.is_private or mapped_ipv4.is_loopback or 
                            mapped_ipv4.is_link_local or mapped_ipv4.is_reserved):
                            return False
                        if str(mapped_ipv4).startswith('169.254.'):
                            return False
                    # Check for 6to4 and Teredo tunneling
                    if ip_obj.sixtofour or ip_obj.teredo:
                        # Block tunneling mechanisms as they can obscure the real target
                        return False
                
                # Block private, loopback, link-local, multicast
                if (ip_obj.is_private or ip_obj.is_loopback or 
                    ip_obj.is_link_local or ip_obj.is_multicast or
                    ip_obj.is_reserved):
                    return False
                # Block metadata endpoints
                if str(ip_obj).startswith('169.254.'):
                    return False
            except ValueError:
                # Not an IP literal, continue with hostname validation
                pass
            
            # Block localhost and loopback hostnames
            if hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1', '0:0:0:0:0:0:0:1']:
                return False
            
            # Block internal domains
            blocked_domains = ['internal', 'localhost', 'local', 'intranet']
            for blocked in blocked_domains:
                if blocked in hostname:
                    return False
            
            # Resolve hostname to all IPs (IPv4 and IPv6) and validate each
            try:
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for family, socktype, proto, canonname, sockaddr in addr_info:
                    ip = sockaddr[0]
                    try:
                        ip_obj = ipaddress.ip_address(ip)
                        
                        # Check for IPv4-mapped IPv6 addresses in resolved IPs
                        if isinstance(ip_obj, ipaddress.IPv6Address):
                            if ip_obj.ipv4_mapped:
                                mapped_ipv4 = ip_obj.ipv4_mapped
                                if (mapped_ipv4.is_private or mapped_ipv4.is_loopback or 
                                    mapped_ipv4.is_link_local or mapped_ipv4.is_reserved):
                                    return False
                                if str(mapped_ipv4).startswith('169.254.'):
                                    return False
                            if ip_obj.sixtofour or ip_obj.teredo:
                                return False
                        
                        # Block any private/internal IPs
                        if (ip_obj.is_private or ip_obj.is_loopback or 
                            ip_obj.is_link_local or ip_obj.is_multicast or
                            ip_obj.is_reserved):
                            return False
                        # Block metadata endpoints
                        if str(ip_obj).startswith('169.254.'):
                            return False
                    except ValueError:
                        # Invalid IP, block it
                        return False
            except socket.gaierror:
                # Can't resolve hostname - block it for safety
                return False
            except Exception as e:
                print(f"Error resolving hostname {hostname}: {str(e)}")
                return False
            
            return True
        except Exception as e:
            print(f"Error validating URL: {str(e)}")
            return False
    
    def _fetch_url(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Fetch HTML content from a URL with security protections.
        
        Args:
            url: URL to fetch (must be validated first)
            timeout: Request timeout in seconds
        
        Returns:
            HTML content as string or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            max_size = 10 * 1024 * 1024  # 10 MB
            max_redirects = 3
            current_url = url
            
            for redirect_count in range(max_redirects + 1):
                # Stream response to enforce size limit during download
                response = requests.get(
                    current_url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=False,
                    stream=True
                )
                
                # Handle redirects manually with proper validation
                if response.status_code in [301, 302, 303, 307, 308]:
                    redirect_location = response.headers.get('Location')
                    if not redirect_location:
                        raise ValueError("Redirect without Location header")
                    
                    # Resolve relative URLs properly
                    if redirect_location.startswith('/') or not redirect_location.startswith('http'):
                        redirect_url = urljoin(current_url, redirect_location)
                    else:
                        redirect_url = redirect_location
                    
                    # Validate the redirect target
                    if not self._validate_url(redirect_url):
                        raise ValueError(f"Redirect to unsafe URL blocked: {redirect_url}")
                    
                    current_url = redirect_url
                    response.close()
                    continue
                
                # Not a redirect, check status and read content
                response.raise_for_status()
                
                # Read response in chunks to enforce size limit
                content_chunks = []
                total_size = 0
                
                for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
                    if chunk:
                        total_size += len(chunk)
                        if total_size > max_size:
                            response.close()
                            raise ValueError(f"Response too large (>{max_size} bytes)")
                        content_chunks.append(chunk)
                
                response.close()
                
                # Decode content
                content_bytes = b''.join(content_chunks)
                try:
                    # Try to detect encoding from response
                    encoding = response.encoding or 'utf-8'
                    return content_bytes.decode(encoding, errors='replace')
                except Exception:
                    return content_bytes.decode('utf-8', errors='replace')
            
            raise ValueError(f"Too many redirects (>{max_redirects})")
            
        except Exception as e:
            print(f"Error fetching URL {url}: {str(e)}")
            return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Extract clean text from HTML content.
        
        Args:
            html_content: Raw HTML content
        
        Returns:
            Cleaned text content
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            max_length = 50000
            if len(text) > max_length:
                text = text[:max_length] + "... [truncated]"
            
            return text
        except Exception as e:
            print(f"Error extracting text from HTML: {str(e)}")
            return ""
    
    async def _extract_products_with_ai(
        self,
        url: str,
        text_content: str,
        html_content: str
    ) -> List[Dict[str, Any]]:
        """
        Use OpenAI to extract product information from webpage content.
        
        Args:
            url: Original URL
            text_content: Cleaned text content
            html_content: Raw HTML content (for additional context)
        
        Returns:
            List of extracted products
        """
        system_prompt = """You are an expert at extracting product information from webpages.
Your task is to analyze webpage content and extract structured product information for CCTV/security camera equipment.

Extract products with the following details:
- name: Product name/title
- description: Full product description
- sku: SKU or product code (if available)
- price: Price (extract numeric value if available)
- currency: Currency code (USD, EUR, etc.) if price is available
- quantity: Default to 1
- specifications: Dict of technical specs (resolution, form_factor, outdoor, poe, ir_range, etc.)
- brand: Brand/manufacturer name if identifiable

Return your response as JSON in this format:
{
    "products": [
        {
            "name": "Product Name",
            "description": "Product description",
            "sku": "SKU-123" or null,
            "price": 299.99 or null,
            "currency": "USD" or null,
            "quantity": 1,
            "specifications": {
                "resolution": "5MP",
                "form_factor": "dome",
                "outdoor": true,
                "poe": true,
                "ir_range": "30m"
            },
            "brand": "Axis" or null
        }
    ]
}

If no products are found, return {"products": []}.
"""

        user_prompt = f"""Extract product information from this webpage:

URL: {url}

Content:
{text_content}

Please extract all products/items found on this page with their specifications."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("products", [])
        except Exception as e:
            print(f"Error extracting products with AI: {str(e)}")
            return []
    
    async def merge_products_into_quote(
        self,
        quote_id: str,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge extracted products into an existing quote.
        
        Args:
            quote_id: ID of the quote to merge products into
            products: List of products to add
        
        Returns:
            Updated quote data
        """
        from app.services.quote_service import QuoteService
        
        quote_service = QuoteService(self.db_conn)
        
        quote = await quote_service.get_quote(quote_id)
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")
        
        current_items = quote.get('items', [])
        
        new_items = []
        for product in products:
            item = {
                "sku": product.get("sku") or f"EXTERNAL-{len(current_items) + len(new_items) + 1}",
                "description": product.get("description") or product.get("name", "Unknown Product"),
                "quantity": product.get("quantity", 1),
                "unit_price": product.get("price"),
                "currency": product.get("currency", quote.get("currency", "USD")),
                "specifications": product.get("specifications", {}),
                "brand": product.get("brand"),
                "source": "url_scan"
            }
            
            if item["unit_price"] is not None:
                item["subtotal"] = item["unit_price"] * item["quantity"]
            else:
                item["unit_price"] = 0.0
                item["subtotal"] = 0.0
            
            new_items.append(item)
        
        updated_items = current_items + new_items
        
        updated_quote = await quote_service.update_quote(
            quote_id,
            {"items": updated_items}
        )
        
        return {
            "quote_id": quote_id,
            "added_items": len(new_items),
            "total_items": len(updated_items),
            "new_items": new_items,
            "updated_quote": updated_quote
        }
