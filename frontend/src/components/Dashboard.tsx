import React, { useState, useEffect, useCallback } from 'react';
import { Row, Col, Card, Button, Alert, Spinner, Badge, Table } from 'react-bootstrap';
import { documentApi, Document } from '../services/api';
import FileUpload from './FileUpload';
import DocumentList from './DocumentList';
import MetricsCards from './MetricsCards';

const Dashboard: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      setError(null);
      const docs = await documentApi.getDocuments();
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    
    // Set up polling for document status updates
    const interval = setInterval(() => {
      loadDocuments();
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [loadDocuments]);

  const handleUploadSuccess = (message: string) => {
    setUploadSuccess(message);
    setTimeout(() => setUploadSuccess(null), 5000);
    loadDocuments(); // Refresh the list
  };

  const handleUploadError = (error: string) => {
    setError(error);
    setTimeout(() => setError(null), 5000);
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDocuments();
  };

  if (loading) {
    return (
      <div className="loading-spinner">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
      </div>
    );
  }

  return (
    <div className="dashboard fade-in">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h1>Document Extraction Dashboard</h1>
            <Button 
              variant="outline-primary" 
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? (
                <>
                  <Spinner
                    as="span"
                    animation="border"
                    size="sm"
                    role="status"
                    aria-hidden="true"
                    className="me-2"
                  />
                  Refreshing...
                </>
              ) : (
                'Refresh'
              )}
            </Button>
          </div>
        </Col>
      </Row>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {uploadSuccess && (
        <Alert variant="success" dismissible onClose={() => setUploadSuccess(null)}>
          {uploadSuccess}
        </Alert>
      )}

      {/* Metrics Cards */}
      <MetricsCards documents={documents} />

      <Row className="mb-4">
        <Col lg={4}>
          <Card className="h-100">
            <Card.Header>
              <Card.Title className="mb-0">Upload Document</Card.Title>
            </Card.Header>
            <Card.Body>
              <FileUpload 
                onSuccess={handleUploadSuccess}
                onError={handleUploadError}
              />
            </Card.Body>
          </Card>
        </Col>
        
        <Col lg={8}>
          <Card className="h-100">
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <Card.Title className="mb-0">Recent Documents</Card.Title>
                <Badge bg="secondary">{documents.length} total</Badge>
              </div>
            </Card.Header>
            <Card.Body>
              <DocumentList 
                documents={documents.slice(0, 10)} // Show only recent 10
                onRefresh={loadDocuments}
              />
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* All Documents Table */}
      <Row>
        <Col>
          <Card>
            <Card.Header>
              <Card.Title className="mb-0">All Documents</Card.Title>
            </Card.Header>
            <Card.Body>
              {documents.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-muted">No documents uploaded yet.</p>
                  <p className="text-muted">Upload your first PDF to get started!</p>
                </div>
              ) : (
                <div className="table-responsive">
                  <Table striped hover>
                    <thead>
                      <tr>
                        <th>Filename</th>
                        <th>Upload Time</th>
                        <th>Status</th>
                        <th>OCR Confidence</th>
                        <th>Extraction Confidence</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.id}>
                          <td>{doc.filename}</td>
                          <td>{new Date(doc.upload_timestamp).toLocaleString()}</td>
                          <td>
                            <Badge 
                              bg={getStatusColor(doc.processing_status)}
                              className={`status-badge status-${doc.processing_status.replace('_', '-')}`}
                            >
                              {doc.processing_status.replace('_', ' ').toUpperCase()}
                            </Badge>
                          </td>
                          <td>
                            {doc.ocr_confidence ? (
                              <Badge bg={getConfidenceColor(doc.ocr_confidence)}>
                                {Math.round(doc.ocr_confidence * 100)}%
                              </Badge>
                            ) : (
                              <span className="text-muted">-</span>
                            )}
                          </td>
                          <td>
                            {doc.extraction_confidence ? (
                              <Badge bg={getConfidenceColor(doc.extraction_confidence)}>
                                {Math.round(doc.extraction_confidence * 100)}%
                              </Badge>
                            ) : (
                              <span className="text-muted">-</span>
                            )}
                          </td>
                          <td>
                            <div className="d-flex gap-2">
                              <Button 
                                size="sm" 
                                variant="outline-primary"
                                href={`/documents/${doc.id}`}
                              >
                                View
                              </Button>
                              {doc.requires_review && !doc.review_completed && (
                                <Button 
                                  size="sm" 
                                  variant="warning"
                                  href={`/review/${doc.id}`}
                                >
                                  Review
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
      return 'primary';
    case 'failed':
      return 'danger';
    case 'review_required':
      return 'warning';
    default:
      return 'secondary';
  }
};

const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'success';
  if (confidence >= 0.6) return 'warning';
  return 'danger';
};

export default Dashboard;