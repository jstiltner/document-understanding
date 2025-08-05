import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/upload': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/documents': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/fields': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/monitoring': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/integration': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/dev': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          bootstrap: ['bootstrap', 'react-bootstrap'],
          router: ['react-router-dom'],
          utils: ['axios']
        }
      }
    }
  },
  define: {
    // Define global constants
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'axios', 'bootstrap', 'react-bootstrap']
  }
})