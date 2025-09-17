# Product Data Loading

This document describes how to load product data from CSV files into the database.

## 📁 Data Files

The system loads product data from CSV files in the `data/` directory:

- **`Axis_price_list_formatted_with_families.csv`** - 1,717 Axis products
- **`hanwha_price_list_formatted_with_families_fixed.csv`** - 1,347 Hanwha products  
- **`i-pro_price_list_formatted_with_families_clean.csv`** - 527 I-Pro products

**Total: 3,591 products**

## 🚀 Loading Scripts

### 1. `load_products_simple.py` (RECOMMENDED)
- **Simple and reliable** data loading script
- Loads basic required fields first
- Handles CSV parsing and data validation
- Creates brands automatically from filenames

```bash
python3 load_products_simple.py
```

### 2. `load_product_data.py` (ADVANCED)
- **Comprehensive** data loading with feature extraction
- Extracts form factors, accessories, and technical features
- More complex but provides richer data
- Includes intelligent parsing of product descriptions

```bash
python3 load_product_data.py
```

### 3. `check_loaded_data.py` (VERIFICATION)
- **Verifies** loaded data and shows statistics
- Displays sample products and family distribution
- Shows brand counts and product status

```bash
python3 check_loaded_data.py
```

## 📊 Data Structure

### CSV Format
Each CSV file contains the following columns:
- **`sku`** - Product SKU/part number
- **`description`** - Product description
- **`price`** - Product price (numeric)
- **`currency`** - Currency code (USD, CAD, etc.)
- **`family`** - Product family/category
- **`status`** - Product status (active/inactive)

### Database Mapping
- **Brand name** extracted from filename (Axis, Hanwha, I-Pro)
- **Status** converted to boolean `active` field
- **Search text** created from SKU + description + family
- **Raw JSON** stores original CSV row for audit

## 🏷️ Brand Extraction

Brand names are automatically extracted from filenames:
- `Axis_price_list_...` → **Axis**
- `hanwha_price_list_...` → **Hanwha**
- `i-pro_price_list_...` → **I-Pro**

## 📈 Loaded Data Summary

### Products by Brand
- **Axis**: 1,717 products (47.8%)
- **Hanwha**: 1,347 products (37.5%)
- **I-Pro**: 527 products (14.7%)

### Product Families
- **Cameras**: 925 products (25.8%)
- **Recorder accessories**: 713 products (19.9%)
- **Access**: 471 products (13.1%)
- **Audio and power accessories**: 422 products (11.8%)
- **Software and licensing**: 350 products (9.7%)
- **Power Supply**: 235 products (6.5%)
- **Recordings**: 217 products (6.0%)
- **Video Management System**: 115 products (3.2%)
- **Switches**: 111 products (3.1%)
- **Alarms**: 19 products (0.5%)

### Product Status
- **Active**: 3,591 products (100%)
- **Inactive**: 0 products (0%)

## 🔧 Technical Details

### Database Schema
- Products stored in `products` table
- Brands stored in `brands` table
- Full-text search enabled with `tsvector`
- JSONB storage for raw CSV data

### Data Validation
- SKU and description are required
- Price parsing handles various formats
- Currency codes normalized to uppercase
- Status converted to boolean active field

### Search Capabilities
- Full-text search on product descriptions
- Trigram search for fuzzy matching
- Search text includes SKU, description, and family
- GIN indexes for fast searching

## 🚨 Error Handling

The loading scripts include comprehensive error handling:
- **Missing data**: Skips rows with missing SKU or description
- **Price parsing**: Handles various price formats gracefully
- **Database errors**: Continues loading after individual row errors
- **Progress tracking**: Shows loading progress every 100 products

## 🔄 Re-loading Data

To reload data after schema changes:

1. **Drop existing data**:
   ```bash
   python3 recreate_database_safe.py
   ```

2. **Load fresh data**:
   ```bash
   python3 load_products_simple.py
   ```

3. **Verify data**:
   ```bash
   python3 check_loaded_data.py
   ```

## 📝 Notes

- All products are loaded as **active** by default
- Brand relationships are automatically created
- Search text is generated for full-text search
- Raw CSV data is preserved in JSONB format
- The system handles different CSV delimiters automatically
