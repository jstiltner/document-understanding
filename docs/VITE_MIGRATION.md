# Vite Migration Guide

This document explains the migration from Create React App (CRA) to Vite for improved development experience and performance.

## 🚀 Why Vite?

### **Performance Benefits**
- **Lightning Fast Dev Server**: Instant server start (vs 10-30s with CRA)
- **Hot Module Replacement (HMR)**: Sub-second updates during development
- **Optimized Builds**: Faster production builds with better tree-shaking
- **Native ES Modules**: Leverages modern browser capabilities

### **Developer Experience**
- **Modern Tooling**: Built on esbuild and Rollup for optimal performance
- **Better TypeScript Support**: Faster type checking and compilation
- **Plugin Ecosystem**: Rich ecosystem of Vite plugins
- **Framework Agnostic**: Not tied to specific React versions

## 📋 Migration Changes

### **Package.json Updates**
```json
{
  "scripts": {
    "dev": "vite",           // was: "start": "react-scripts start"
    "build": "tsc && vite build", // was: "build": "react-scripts build"
    "preview": "vite preview",    // new: preview production build
    "test": "vitest"              // was: "test": "react-scripts test"
  }
}
```

### **New Configuration Files**
- **`vite.config.ts`**: Main Vite configuration
- **`tsconfig.node.json`**: TypeScript config for Node.js files
- **`vitest.config.ts`**: Testing configuration
- **`.eslintrc.cjs`**: Updated ESLint configuration

### **File Structure Changes**
```
frontend/
├── index.html          # Moved from public/ to root (Vite requirement)
├── public/             # Static assets (no index.html)
├── src/
│   ├── test/
│   │   └── setup.ts    # Test setup for Vitest
│   └── ...
├── vite.config.ts      # Vite configuration
├── vitest.config.ts    # Test configuration
├── tsconfig.json       # Updated for Vite
└── tsconfig.node.json  # Node.js TypeScript config
```

### **HTML Template Changes**
```html
<!-- Old CRA index.html -->
<link rel="icon" href="%PUBLIC_URL%/favicon.ico" />

<!-- New Vite index.html -->
<link rel="icon" type="image/svg+xml" href="/favicon.ico" />
<script type="module" src="/src/index.tsx"></script>
```

## ⚙️ Configuration Details

### **Vite Configuration (`vite.config.ts`)**
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',  // API proxy configuration
      '/auth': 'http://localhost:8000',
      // ... other routes
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
          // ... optimized chunking
        }
      }
    }
  }
})
```

### **Testing with Vitest**
- **Faster**: 10x faster than Jest in most cases
- **ESM Native**: No configuration needed for ES modules
- **Vite Integration**: Shares configuration with development server
- **Jest Compatible**: Most Jest APIs work without changes

### **TypeScript Configuration**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    // ... optimized for Vite
  }
}
```

## 🔄 Development Workflow Changes

### **Starting Development**
```bash
# Old CRA command
npm start

# New Vite command
npm run dev
```

### **Building for Production**
```bash
# Old CRA command
npm run build

# New Vite command
npm run build  # Includes TypeScript compilation
```

### **Testing**
```bash
# Old CRA command
npm test

# New Vite command
npm run test      # Run tests once
npm run test:ui   # Run with UI interface
```

## 📦 Dependency Changes

### **Removed Dependencies**
- `react-scripts` - No longer needed
- `@testing-library/jest-dom` - Replaced with Vitest equivalent
- Various CRA-specific packages

### **Added Dependencies**
- `vite` - Build tool and dev server
- `@vitejs/plugin-react` - React support for Vite
- `vitest` - Testing framework
- `@vitest/ui` - Testing UI interface
- `jsdom` - DOM environment for testing

## 🚀 Performance Improvements

### **Development Server**
- **Startup Time**: ~50ms (vs 10-30s with CRA)
- **HMR Speed**: <100ms for most changes
- **Memory Usage**: ~50% less than CRA dev server

### **Build Performance**
- **Build Time**: 2-5x faster than CRA
- **Bundle Size**: 10-20% smaller with better tree-shaking
- **Code Splitting**: More granular and efficient

## 🔧 Troubleshooting

### **Common Issues**

#### **Import Errors**
```typescript
// ❌ Old CRA style
import logo from './logo.svg';

// ✅ Vite style (explicit imports)
import logo from './logo.svg?url';
```

#### **Environment Variables**
```bash
# ❌ CRA style
REACT_APP_API_URL=http://localhost:8000

# ✅ Vite style
VITE_API_URL=http://localhost:8000
```

#### **Public Assets**
```typescript
// ❌ CRA style
<img src={process.env.PUBLIC_URL + '/logo.png'} />

// ✅ Vite style
<img src="/logo.png" />
```

### **Migration Checklist**
- [ ] Update package.json scripts
- [ ] Move index.html to root directory
- [ ] Update HTML template (remove %PUBLIC_URL%)
- [ ] Create Vite configuration files
- [ ] Update TypeScript configuration
- [ ] Update environment variables (REACT_APP_ → VITE_)
- [ ] Test all functionality
- [ ] Update CI/CD scripts

## 📚 Additional Resources

- **Vite Documentation**: https://vitejs.dev/
- **Vite React Plugin**: https://github.com/vitejs/vite-plugin-react
- **Vitest Documentation**: https://vitest.dev/
- **Migration Guide**: https://vitejs.dev/guide/migration.html

## 🎯 Benefits Realized

After migration, developers will experience:
- **Instant Development Server**: No more waiting for compilation
- **Real-time Updates**: Changes reflect immediately in browser
- **Faster Builds**: Production builds complete in seconds, not minutes
- **Better Developer Experience**: Modern tooling with excellent error messages
- **Future-Proof**: Built on modern web standards and actively maintained

The migration to Vite significantly improves the development experience while maintaining full compatibility with existing React components and functionality.