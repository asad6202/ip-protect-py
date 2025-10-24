export type Brand = {
    id: string
    name: string
    slug?: string | null
    created_at: string
    updated_at: string
    product_count: number
  }

  export type CreateBrandRequest = {
    name: string
    slug?: string | null
  }

  export type UpdateBrandRequest = {
    name?: string
    slug?: string | null
  }
  
  export type Product = {
    id: string
    brand_id?: string | null
    sku: string
    description: string
    price: number
    currency: string
    family: string
    status: string
    form_factor?: string | null
    outdoor?: boolean | null
    poe?: boolean | null
    poe_plus?: boolean | null
    ir_range_m?: number | null
    resolution_mp?: number | null
    vandal_ik10?: boolean | null
    nvr_channels?: number | null
    switch_ports?: number | null
    is_accessory: boolean
    accessory_type?: string | null
    created_at: string
    updated_at: string
  }
  
  export type ProductUpload = {
    id: string
    brand_id?: string | null
    original_name: string
    stored_path: string
    row_count?: number | null
    status: 'uploaded' | 'processing' | 'processed' | 'failed'
    message?: string | null
    created_at: string
    processed_at?: string | null
  }
  
  export type QuoteItem = {
    id?: string
    sku: string
    description: string
    quantity: number
    unit_price: number
    currency: string
    subtotal: number
    product_id?: string | null
    metadata?: any
    feedback_insights?: any
  }
  
  export type Quote = {
    id: string
    title?: string | null
    prompt: string
    extracted_intent?: any
    currency?: string | null
    total_amount?: number | null
    notes?: string | null
    status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired'
    created_at: string
    updated_at: string
    items?: QuoteItem[]
  }
  
  export type Feedback = {
    id: string
    quote_id: string
    rating?: number | null
    comment?: string | null
    labels?: any
    corrections?: any
    created_at: string
  }
  
  export type RuleSet = {
    id: string
    name: string
    is_active: boolean
    priority: number
    created_at: string
    updated_at: string
  }
  
  export type Rule = {
    id: string
    rule_set_id: string
    name: string
    active: boolean
    scope: 'global' | 'item'
    priority: number
    condition: any
    actions: any
    nlp_command?: string | null
    created_at: string
    updated_at: string
  }
  
  export type PromptRun = {
    id: string
    prompt: string
    extracted_intent?: any
    rules_applied?: any
    result_quote_id?: string | null
    created_at: string
  }
  
  export type QuoteGenResponse = {
    items: QuoteItem[]
    total: number
    currency: string
    notes?: string | null
  }
  
  // API Request/Response types
  
  export type CreateQuoteRequest = {
    title?: string
    prompt: string
    extracted_intent?: unknown
    currency?: string
    items: Array<{
      product_id?: string | null
      sku: string
      description: string
      quantity: number
      unit_price: number
      currency: string
      subtotal: number
      metadata?: unknown
    }>
    notes?: string
    feedback?: CreateFeedbackRequest
  }
  
  export type UpdateQuoteRequest = Partial<CreateQuoteRequest> & {
    status?: string
  }
  
  export type CreateFeedbackRequest = {
    rating?: 1 | 2 | 3 | 4 | 5
    comment?: string
    labels?: any
    corrections?: any
  }

  export type QuoteItemFeedback = {
    id: string
    quote_item_id: string
    quote_id: string
    feedback_type: 'correct' | 'incorrect' | 'missing' | 'wrong_quantity' | 'wrong_price' | 'wrong_specs'
    rating?: number | null
    comment?: string | null
    suggested_sku?: string | null
    suggested_quantity?: number | null
    suggested_price?: number | null
    correction_data?: any
    user_context?: any
    created_at: string
    updated_at: string
  }

  export type CreateItemFeedbackRequest = {
    feedback_type: 'correct' | 'incorrect' | 'missing' | 'wrong_quantity' | 'wrong_price' | 'wrong_specs'
    comment?: string
    suggested_sku?: string
    suggested_quantity?: number
    suggested_price?: number
    correction_data?: any
    user_context?: any
  }
  
  export type CreateRuleSetRequest = {
    name: string
    is_active?: boolean
    priority?: number
  }
  
  export type UpdateRuleSetRequest = {
    name?: string
    is_active?: boolean
    priority?: number
  }
  
  export type CreateRuleRequest = {
    rule_set_id: string
    name: string
    active?: boolean
    scope: 'global' | 'item'
    priority?: number
    condition: any
    actions: any
  }
  
  export type UpdateRuleRequest = {
    name?: string
    active?: boolean
    scope?: 'global' | 'item'
    priority?: number
    condition?: any
    actions?: any
  }
  
  // Pagination types
  export type PaginatedResponse<T> = {
    items: T[]
    total: number
    page: number
    page_size: number
    pages: number
  }
  
  export type PaginationParams = {
    page?: number
    page_size?: number
  }
  
  // Filter types
  export type ProductFilters = {
    brand_id?: string
    search?: string
    family?: string
    is_accessory?: boolean
  } & PaginationParams
  