import { createBrowserRouter } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './features/dashboard/DashboardPage'
import BrandListPage from './features/brands/pages/BrandListPage'
import BrandDetailPage from './features/brands/pages/BrandDetailPage'
import ProductListPage from './features/products/pages/ProductListPage'
import ProductDetailPage from './features/products/pages/ProductDetailPage'
import QuoteListPage from './features/quotes/pages/QuoteListPage'
import QuoteCreateFromPromptPage from './features/quotes/pages/QuoteCreateFromPromptPage'
import QuoteDetailPage from './features/quotes/pages/QuoteDetailPage'
import RuleSetListPage from './features/rules/pages/RuleSetListPage'
import RuleSetDetailPage from './features/rules/pages/RuleSetDetailPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'brands',
        children: [
          {
            index: true,
            element: <BrandListPage />,
          },
          {
            path: ':id',
            element: <BrandDetailPage />,
          },
        ],
      },
      {
        path: 'products',
        children: [
          {
            index: true,
            element: <ProductListPage />,
          },
          {
            path: ':id',
            element: <ProductDetailPage />,
          },
        ],
      },
      {
        path: 'quotes',
        children: [
          {
            index: true,
            element: <QuoteListPage />,
          },
          {
            path: 'new',
            element: <QuoteCreateFromPromptPage />,
          },
          {
            path: ':id',
            element: <QuoteDetailPage />,
          },
        ],
      },
      {
        path: 'rules',
        children: [
          {
            index: true,
            element: <RuleSetListPage />,
          },
          {
            path: ':id',
            element: <RuleSetDetailPage />,
          },
        ],
      },
    ],
  },
])
