import React from 'react';
import { ListGroup, Badge, Button } from 'react-bootstrap';
import { Document } from '../services/api';

interface DocumentListProps {
  documents: Document[];
  onRefresh: () => void;
}

const DocumentList: React.FC<DocumentListProps> = ({ documents, onRefresh }) => {
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

  if (documents.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-muted">No documents found.</p>
        <Button variant="outline-primary" size="sm" onClick={onRefresh}>
          Refresh
        </Button>
      </div>
    );
  }

  return (
    <ListGroup>
      {documents.map((doc) => (
        <ListGroup.Item
          key={doc.id}
          className="d-flex justify-content-between align-items-start"
        >
          <div className="flex-grow-1">
            <div className="fw-bold">{doc.filename}</div>
            <small className="text-muted">
              {new Date(doc.upload_timestamp).toLocaleString()}
            </small>
            <div className="mt-1">
              <Badge 
                bg={getStatusColor(doc.processing_status)}
                className="me-2"
              >
                {doc.processing_status.replace('_', ' ').toUpperCase()}
              </Badge>
              {doc.extraction_confidence && (
                <Badge bg={getConfidenceColor(doc.extraction_confidence)}>
                  {Math.round(doc.extraction_confidence * 100)}%
                </Badge>
              )}
            </div>
          </div>
          <div className="d-flex flex-column gap-1">
            <Button size="sm" variant="outline-primary" href={`/documents/${doc.id}`}>
              View
            </Button>
            {doc.requires_review && !doc.review_completed && (
              <Button size="sm" variant="warning" href={`/review/${doc.id}`}>
                Review
              </Button>
            )}
          </div>
        </ListGroup.Item>
      ))}
    </ListGroup>
  );
};

export default DocumentList;