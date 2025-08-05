import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Row, Col, Card, Button, Form, Alert, Spinner, Badge, Tabs, Tab } from 'react-bootstrap';
import { documentApi, ReviewDocument } from '../services/api';

const DocumentReview: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  
  const [document, setDocument] = useState<ReviewDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editedFields, setEditedFields] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<string>('fields');

  useEffect(() => {
    if (documentId) {
      loadDocument(parseInt(documentId));
    }
  }, [documentId]);

  const loadDocument = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const doc = await documentApi.getDocumentForReview(id);
      setDocument(doc);
      
      // Initialize edited fields with current values
      const initialFields: Record<string, string> = {};
      Object.entries(doc.required_fields).forEach(([key, field]) => {
        initialFields[key] = field.value || '';
      });
      Object.entries(doc.optional_fields).forEach(([key, field]) => {
        initialFields[key] = field.value || '';
      });
      setEditedFields(initialFields);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldName: string, value: string) => {
    setEditedFields(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const handleSave = async () => {
    if (!document) return;

    setSaving(true);
    try {
      // Here you would typically call an API to save the reviewed fields
      // For now, we'll just simulate the save
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Navigate back to dashboard
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'danger';
  };

  const getConfidenceText = (confidence: number): string => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
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

  if (error || !document) {
    return (
      <Alert variant="danger">
        <Alert.Heading>Error</Alert.Heading>
        <p>{error || 'Document not found'}</p>
        <Button variant="outline-danger" onClick={() => navigate('/')}>
          Back to Dashboard
        </Button>
      </Alert>
    );
  }

  return (
    <div className="document-review fade-in">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h1>Document Review</h1>
              <p className="text-muted mb-0">
                {document.filename} • Overall Confidence: {' '}
                <Badge bg={getConfidenceColor(document.overall_confidence)}>
                  {Math.round(document.overall_confidence * 100)}% ({getConfidenceText(document.overall_confidence)})
                </Badge>
              </p>
            </div>
            <div className="d-flex gap-2">
              <Button variant="outline-secondary" onClick={() => navigate('/')}>
                Cancel
              </Button>
              <Button 
                variant="primary" 
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save & Complete Review'}
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k || 'fields')} className="mb-4">
        <Tab eventKey="fields" title="Field Review">
          <Row>
            <Col lg={8}>
              {/* Required Fields */}
              <Card className="mb-4">
                <Card.Header>
                  <Card.Title className="mb-0">
                    Required Fields
                    <Badge bg="danger" className="ms-2">
                      {Object.keys(document.required_fields).length}
                    </Badge>
                  </Card.Title>
                </Card.Header>
                <Card.Body>
                  {Object.entries(document.required_fields).map(([fieldName, field]) => (
                    <div key={fieldName} className="field-item">
                      <div className="field-label">{fieldName}</div>
                      <div className="field-value">
                        <Form.Control
                          type="text"
                          value={editedFields[fieldName] || ''}
                          onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                          placeholder={`Enter ${fieldName}`}
                        />
                        {field.value && field.value !== editedFields[fieldName] && (
                          <Form.Text className="text-muted">
                            Original: "{field.value}"
                          </Form.Text>
                        )}
                      </div>
                      <div className="field-confidence">
                        <Badge bg={getConfidenceColor(field.confidence)}>
                          {Math.round(field.confidence * 100)}%
                        </Badge>
                      </div>
                    </div>
                  ))}
                </Card.Body>
              </Card>

              {/* Optional Fields */}
              <Card>
                <Card.Header>
                  <Card.Title className="mb-0">
                    Optional Fields
                    <Badge bg="info" className="ms-2">
                      {Object.keys(document.optional_fields).length}
                    </Badge>
                  </Card.Title>
                </Card.Header>
                <Card.Body>
                  {Object.entries(document.optional_fields).map(([fieldName, field]) => (
                    <div key={fieldName} className="field-item">
                      <div className="field-label">{fieldName}</div>
                      <div className="field-value">
                        <Form.Control
                          type="text"
                          value={editedFields[fieldName] || ''}
                          onChange={(e) => handleFieldChange(fieldName, e.target.value)}
                          placeholder={`Enter ${fieldName}`}
                        />
                        {field.value && field.value !== editedFields[fieldName] && (
                          <Form.Text className="text-muted">
                            Original: "{field.value}"
                          </Form.Text>
                        )}
                      </div>
                      <div className="field-confidence">
                        <Badge bg={getConfidenceColor(field.confidence)}>
                          {Math.round(field.confidence * 100)}%
                        </Badge>
                      </div>
                    </div>
                  ))}
                </Card.Body>
              </Card>
            </Col>

            <Col lg={4}>
              <Card className="sticky-top" style={{ top: '20px' }}>
                <Card.Header>
                  <Card.Title className="mb-0">Review Guidelines</Card.Title>
                </Card.Header>
                <Card.Body>
                  <div className="mb-3">
                    <h6>Confidence Levels:</h6>
                    <div className="d-flex flex-column gap-1">
                      <div>
                        <Badge bg="success" className="me-2">High</Badge>
                        80%+ - Likely accurate
                      </div>
                      <div>
                        <Badge bg="warning" className="me-2">Medium</Badge>
                        60-79% - Verify carefully
                      </div>
                      <div>
                        <Badge bg="danger" className="me-2">Low</Badge>
                        &lt;60% - Requires attention
                      </div>
                    </div>
                  </div>

                  <div className="mb-3">
                    <h6>Required Fields:</h6>
                    <p className="small text-muted">
                      All required fields must be completed for the document to be processed successfully.
                    </p>
                  </div>

                  <div>
                    <h6>Tips:</h6>
                    <ul className="small text-muted">
                      <li>Check the OCR text tab for reference</li>
                      <li>Look for alternative field names or formats</li>
                      <li>Leave optional fields empty if not found</li>
                      <li>Use standard date format: MM/DD/YYYY</li>
                    </ul>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </Tab>

        <Tab eventKey="ocr" title="OCR Text">
          <Card>
            <Card.Header>
              <Card.Title className="mb-0">Original OCR Text</Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="ocr-text">
                {document.ocr_text}
              </div>
            </Card.Body>
          </Card>
        </Tab>
      </Tabs>
    </div>
  );
};

export default DocumentReview;