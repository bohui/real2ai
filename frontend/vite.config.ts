import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Enable React Fast Refresh
      fastRefresh: process.env.NODE_ENV === 'development',
      // Optimize JSX runtime
      jsxRuntime: 'automatic'
    })
  ],
  define: {
    'process.env': {},
    __DEV__: JSON.stringify(process.env.NODE_ENV === 'development')
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@/components': resolve(__dirname, './src/components'),
      '@/pages': resolve(__dirname, './src/pages'),
      '@/hooks': resolve(__dirname, './src/hooks'),
      '@/store': resolve(__dirname, './src/store'),
      '@/utils': resolve(__dirname, './src/utils'),
      '@/types': resolve(__dirname, './src/types'),
      '@/services': resolve(__dirname, './src/services'),
      '@/assets': resolve(__dirname, './src/assets')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV === 'development',
    target: 'es2020', // Better compatibility while maintaining performance
    minify: 'esbuild',
    cssMinify: true,
    reportCompressedSize: false,
    chunkSizeWarningLimit: 500, // More aggressive chunk size limits
    assetsInlineLimit: 4096, // Inline smaller assets
    cssCodeSplit: true, // Enable CSS code splitting
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Create optimized vendor chunks for better caching
          if (id.includes('node_modules')) {
            // Core React ecosystem
            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-core'
            }
            if (id.includes('react-router-dom') || id.includes('react-hook-form')) {
              return 'react-routing'
            }
            
            // UI and animation libraries
            if (id.includes('framer-motion')) {
              return 'framer-motion' // Large library, separate chunk
            }
            if (id.includes('@headlessui/react') || id.includes('lucide-react')) {
              return 'ui-vendor'
            }
            
            // Data management
            if (id.includes('@tanstack/react-query')) {
              return 'react-query' // Large library, separate chunk
            }
            if (id.includes('axios') || id.includes('zustand')) {
              return 'data-vendor'
            }
            
            // PDF and document processing (heavy)
            if (id.includes('react-pdf') || id.includes('pdf')) {
              return 'pdf-vendor'
            }
            
            // Charts and visualization
            if (id.includes('recharts') || id.includes('chart')) {
              return 'charts-vendor'
            }
            
            // Form libraries
            if (id.includes('zod') || id.includes('@hookform/resolvers')) {
              return 'forms-vendor'
            }
            
            // Utilities and smaller libraries
            return 'vendor'
          }
          
          // Application code splitting
          if (id.includes('src/pages/auth')) {
            return 'auth-pages'
          }
          if (id.includes('src/pages')) {
            // Split pages by feature area
            if (id.includes('Dashboard') || id.includes('Analysis')) {
              return 'core-pages'
            }
            return 'feature-pages'
          }
          
          // Component chunking
          if (id.includes('src/components/seo')) {
            return 'seo-components'
          }
          if (id.includes('src/components/performance')) {
            return 'performance-components'
          }
          if (id.includes('src/components/contract')) {
            return 'contract-components'
          }
          if (id.includes('src/components')) {
            return 'components'
          }
          
          // Utilities
          if (id.includes('src/utils')) {
            return 'utils'
          }
        },
        
        // Optimize chunk and asset file names for caching
        entryFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId
          if (facadeModuleId && facadeModuleId.includes('src/main.tsx')) {
            return 'assets/main-[hash].js'
          }
          return 'assets/[name]-[hash].js'
        },
        chunkFileNames: (chunkInfo) => {
          // Use shorter hash for smaller chunks
          if (chunkInfo.name && chunkInfo.name.includes('vendor')) {
            return 'assets/vendor/[name]-[hash:8].js'
          }
          return 'assets/[name]-[hash:8].js'
        },
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.') || []
          const ext = info[info.length - 1]
          
          // Organize assets by type for better CDN caching
          if (/\.(png|jpe?g|svg|gif|tiff|bmp|ico|webp)$/i.test(assetInfo.name || '')) {
            return `assets/images/[name]-[hash:8].${ext}`
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name || '')) {
            return `assets/fonts/[name]-[hash:8].${ext}`
          }
          if (/\.(css)$/i.test(assetInfo.name || '')) {
            return `assets/styles/[name]-[hash:8].${ext}`
          }
          return `assets/[name]-[hash:8].${ext}`
        }
      },
      
      // External dependencies for CDN loading (optional)
      external: process.env.NODE_ENV === 'production' ? [] : []
    }
  },
  // Enhanced optimization settings
  esbuild: {
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
    legalComments: 'none', // Remove license comments in production
    minifyIdentifiers: true,
    minifySyntax: true,
    minifyWhitespace: true,
    treeShaking: true
  },
  
  // Performance optimizations
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'framer-motion',
      'lucide-react',
      'clsx',
      'date-fns'
    ],
    exclude: [
      // Exclude large libraries that benefit from dynamic imports
      'react-pdf',
      'recharts'
    ]
  },
  
  // CSS optimization
  css: {
    devSourcemap: process.env.NODE_ENV === 'development'
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts']
  }
})