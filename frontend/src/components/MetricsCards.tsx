import React from 'react';
import { Row, Col, Card } from 'react-bootstrap';
import { Document } from '../services/api';

interface MetricsCardsProps {
  documents: Document[];
}

const MetricsCards: React.FC<MetricsCardsProps> = ({ documents }) => {
  const totalDocuments = documents.length;
  const completedDocuments = documents.filter(doc => doc.processing_status === 'completed').length;
  const processingDocuments = documents.filter(doc => doc.processing_status === 'processing').length;
  const reviewRequiredDocuments = documents.filter(doc => doc.requires_review && !doc.review_completed).length;
  const failedDocuments = documents.filter(doc => doc.processing_status === 'failed').length;

  const completionRate = totalDocuments > 0 ? (completedDocuments / totalDocuments) * 100 : 0;
  
  const avgExtractionConfidence = documents
    .filter(doc => doc.extraction_confidence !== null && doc.extraction_confidence !== undefined)
    .reduce((sum, doc) => sum + (doc.extraction_confidence || 0), 0) / 
    Math.max(documents.filter(doc => doc.extraction_confidence !== null).length, 1);

  return (
    <Row className="mb-4">
      <Col md={6} lg={3} className="mb-3">
        <Card className="metrics-card h-100">
          <Card.Body className="text-center">
            <div className="metrics-value">{totalDocuments}</div>
            <div className="metrics-label">Total Documents</div>
          </Card.Body>
        </Card>
      </Col>
      
      <Col md={6} lg={3} className="mb-3">
        <Card className="h-100" style={{ background: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)', color: 'white', border: 'none' }}>
          <Card.Body className="text-center">
            <div className="metrics-value">{completedDocuments}</div>
            <div className="metrics-label">Completed</div>
            <small className="opacity-75">
              {completionRate.toFixed(1)}% completion rate
            </small>
          </Card.Body>
        </Card>
      </Col>
      
      <Col md={6} lg={3} className="mb-3">
        <Card className="h-100" style={{ background: 'linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)', color: 'white', border: 'none' }}>
          <Card.Body className="text-center">
            <div className="metrics-value">{reviewRequiredDocuments}</div>
            <div className="metrics-label">Needs Review</div>
            {processingDocuments > 0 && (
              <small className="opacity-75">
                {processingDocuments} processing
              </small>
            )}
          </Card.Body>
        </Card>
      </Col>
      
      <Col md={6} lg={3} className="mb-3">
        <Card className="h-100" style={{ background: 'linear-gradient(135deg, #17a2b8 0%, #6f42c1 100%)', color: 'white', border: 'none' }}>
          <Card.Body className="text-center">
            <div className="metrics-value">
              {avgExtractionConfidence > 0 ? `${Math.round(avgExtractionConfidence * 100)}%` : '-'}
            </div>
            <div className="metrics-label">Avg Confidence</div>
            {failedDocuments > 0 && (
              <small className="opacity-75">
                {failedDocuments} failed
              </small>
            )}
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default MetricsCards;