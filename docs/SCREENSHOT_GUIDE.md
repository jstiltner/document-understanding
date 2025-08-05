# UI Screenshot Capture Guide

This guide helps you capture high-quality screenshots of the Document Understanding API interface for documentation purposes.

## 📋 Required Screenshots

### 1. Dashboard Overview (`dashboard-overview.png`)
- **URL**: http://localhost:3000
- **What to capture**: Main dashboard with metrics cards, recent documents, processing statistics
- **Setup**: Ensure some sample documents are processed to show realistic data
- **Focus**: Overall system health and activity overview

### 2. Document Upload (`document-upload.png`)
- **URL**: http://localhost:3000 (upload section)
- **What to capture**: File upload interface with drag-and-drop area
- **Setup**: Show the upload interface in action or ready state
- **Focus**: User-friendly upload experience

### 3. Document List (`document-list.png`)
- **URL**: http://localhost:3000 (documents section)
- **What to capture**: Document management table with various document statuses
- **Setup**: Have multiple documents with different statuses (processing, completed, review required)
- **Focus**: Document management capabilities and status indicators

### 4. Document Review (`document-review.png`)
- **URL**: http://localhost:3000 (review interface)
- **What to capture**: Side-by-side document view with field editing interface
- **Setup**: Open a document that requires review
- **Focus**: Human review workflow and field correction interface

### 5. API Documentation (`api-documentation.png`)
- **URL**: http://localhost:8000/docs
- **What to capture**: Enhanced Swagger UI with expanded endpoint details
- **Setup**: Expand a few key endpoints to show documentation quality
- **Focus**: Comprehensive API documentation and testing capabilities

### 6. Monitoring Dashboard (`monitoring-dashboard.png`)
- **URL**: http://localhost:8000/monitoring/dashboard
- **What to capture**: System health metrics, charts, and performance indicators
- **Setup**: Ensure system has been running with some activity
- **Focus**: Real-time monitoring and system health visualization

### 7. Batch Processing (`batch-processing.png`)
- **URL**: http://localhost:3000 (batch upload section)
- **What to capture**: Batch upload interface with progress tracking
- **Setup**: Show batch upload in progress or completed state
- **Focus**: Bulk processing capabilities and progress visualization

### 8. Field Configuration (`field-configuration.png`)
- **URL**: http://localhost:3000 (admin/configuration section)
- **What to capture**: Field definition management interface
- **Setup**: Show field definitions with validation rules and extraction hints
- **Focus**: Dynamic configuration capabilities

## 🎨 Screenshot Guidelines

### Technical Requirements
- **Resolution**: 1920x1080 or higher
- **Format**: PNG (for crisp text and UI elements)
- **Browser**: Use Chrome or Firefox for consistent rendering
- **Zoom Level**: 100% (default zoom)

### Visual Guidelines
- **Include Browser Chrome**: Show address bar for context
- **Clean Interface**: Close unnecessary browser tabs and extensions
- **Sample Data**: Use realistic but non-sensitive sample data
- **Consistent Timing**: Capture when UI is fully loaded and stable

### Data Privacy
- **No Real PHI**: Use only sample/test data
- **Anonymize**: Ensure no real patient or sensitive information is visible
- **Generic Names**: Use placeholder names like "John Doe", "Sample Hospital"

## 🛠️ Capture Process

### 1. Setup Development Environment
```bash
# Start the application
./scripts/start-dev.sh

# Generate test data (if needed)
curl http://localhost:8000/dev/generate-test-data
```

### 2. Prepare Sample Data
- Upload a few test documents
- Process them through the pipeline
- Create some documents that require review
- Ensure various document statuses are represented

### 3. Capture Screenshots
- Use browser's built-in screenshot tools or tools like:
  - **macOS**: Cmd+Shift+4 (select area) or Cmd+Shift+3 (full screen)
  - **Windows**: Windows+Shift+S (Snipping Tool)
  - **Linux**: gnome-screenshot or similar

### 4. Post-Processing
- Crop to focus on relevant UI elements
- Ensure text is readable
- Maintain consistent sizing across screenshots
- Optimize file size while maintaining quality

## 📁 File Organization

Save screenshots in the `docs/screenshots/` directory with exact filenames:
```
docs/screenshots/
├── dashboard-overview.png
├── document-upload.png
├── document-list.png
├── document-review.png
├── api-documentation.png
├── monitoring-dashboard.png
├── batch-processing.png
└── field-configuration.png
```

## ✅ Quality Checklist

Before finalizing screenshots:
- [ ] All UI elements are clearly visible
- [ ] Text is crisp and readable
- [ ] No sensitive data is shown
- [ ] Browser chrome is included for context
- [ ] Screenshots show realistic usage scenarios
- [ ] File sizes are optimized (< 2MB each)
- [ ] Consistent visual style across all screenshots

## 🔄 Updating Screenshots

When updating the UI:
1. Update relevant screenshots
2. Maintain consistent naming convention
3. Update this guide if new screenshots are needed
4. Verify all README.md image links still work

---

*These screenshots will significantly enhance the README.md and make the project more appealing to potential users and contributors.*