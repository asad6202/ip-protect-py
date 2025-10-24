import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  optimizeDeps: {
    exclude: [
      'lucide-react',
      '@tanstack/react-query',
      'react-hook-form',
      '@hookform/resolvers',
      'zod',
      'date-fns'
    ]
  },
  server: {
    host: '0.0.0.0', // Important for Replit
    port: 5000,
    strictPort: true,
    allowedHosts: true, // Allow all hosts for Replit
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  preview: {
    host: '0.0.0.0', // Important for Replit
    port: 3000,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false, // Disable sourcemaps for production
  },
})
