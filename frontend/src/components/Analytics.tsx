import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Table, Badge, Alert, Spinner } from 'react-bootstrap';
import axios from 'axios';

interface ModelPerformance {
  model_version: string;
  field_name: string;
  total_predictions: number;
  correct_predictions: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  avg_reward: number;
}

interface PerformanceSummary {
  total_feedback_records: number;
  average_reward: number;
  feedback_distribution: Record<string, number>;
}

const Analytics: React.FC = () => {
  const [performance, setPerformance] = useState<ModelPerformance[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get('/analytics/model-performance');
      setPerformance(response.data.performance_by_field);
      setSummary(response.data.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const getPerformanceColor = (score: number): string => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'danger';
  };

  const getRewardColor = (reward: number): string => {
    if (reward >= 0.5) return 'success';
    if (reward >= 0) return 'warning';
    return 'danger';
  };

  if (loading) {
    return (
      <div className="loading-spinner">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading analytics...</span>
        </Spinner>
      </div>
    );
  }

  return (
    <div className="analytics fade-in">
      <Row className="mb-4">
        <Col>
          <h1>Model Performance Analytics</h1>
          <p className="text-muted">
            Track model performance and reinforcement learning metrics
          </p>
        </Col>
      </Row>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      {summary && (
        <Row className="mb-4">
          <Col md={4}>
            <Card className="h-100" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none' }}>
              <Card.Body className="text-center">
                <div className="metrics-value">{summary.total_feedback_records}</div>
                <div className="metrics-label">Total Feedback Records</div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={4}>
            <Card className="h-100" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white', border: 'none' }}>
              <Card.Body className="text-center">
                <div className="metrics-value">
                  {summary.average_reward >= 0 ? '+' : ''}{summary.average_reward.toFixed(3)}
                </div>
                <div className="metrics-label">Average Reward Score</div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={4}>
            <Card className="h-100" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white', border: 'none' }}>
              <Card.Body className="text-center">
                <div className="metrics-value">
                  {Object.keys(summary.feedback_distribution).length}
                </div>
                <div className="metrics-label">Feedback Types</div>
                <small className="opacity-75">
                  {Object.entries(summary.feedback_distribution).map(([type, count]) => (
                    <div key={type}>{type}: {count}</div>
                  ))}
                </small>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {/* Performance by Field */}
      <Card>
        <Card.Header>
          <Card.Title className="mb-0">Performance by Field</Card.Title>
        </Card.Header>
        <Card.Body>
          {performance.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-muted">No performance data available yet.</p>
              <p className="text-muted">Performance metrics will appear after document reviews are completed.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <Table striped hover>
                <thead>
                  <tr>
                    <th>Model Version</th>
                    <th>Field Name</th>
                    <th>Total Predictions</th>
                    <th>Accuracy</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1 Score</th>
                    <th>Avg Reward</th>
                    <th>False Positives</th>
                    <th>False Negatives</th>
                  </tr>
                </thead>
                <tbody>
                  {performance.map((perf, index) => {
                    const accuracy = perf.total_predictions > 0 
                      ? perf.correct_predictions / perf.total_predictions 
                      : 0;
                    
                    return (
                      <tr key={index}>
                        <td>
                          <code className="small">{perf.model_version}</code>
                        </td>
                        <td>
                          <strong>{perf.field_name}</strong>
                        </td>
                        <td>{perf.total_predictions}</td>
                        <td>
                          <Badge bg={getPerformanceColor(accuracy)}>
                            {Math.round(accuracy * 100)}%
                          </Badge>
                        </td>
                        <td>
                          <Badge bg={getPerformanceColor(perf.precision)}>
                            {Math.round(perf.precision * 100)}%
                          </Badge>
                        </td>
                        <td>
                          <Badge bg={getPerformanceColor(perf.recall)}>
                            {Math.round(perf.recall * 100)}%
                          </Badge>
                        </td>
                        <td>
                          <Badge bg={getPerformanceColor(perf.f1_score)}>
                            {perf.f1_score.toFixed(3)}
                          </Badge>
                        </td>
                        <td>
                          <Badge bg={getRewardColor(perf.avg_reward)}>
                            {perf.avg_reward >= 0 ? '+' : ''}{perf.avg_reward.toFixed(3)}
                          </Badge>
                        </td>
                        <td>
                          <span className="text-danger">{perf.false_positives}</span>
                        </td>
                        <td>
                          <span className="text-warning">{perf.false_negatives}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Performance Insights */}
      <Row className="mt-4">
        <Col>
          <Card>
            <Card.Header>
              <Card.Title className="mb-0">Performance Insights</Card.Title>
            </Card.Header>
            <Card.Body>
              <Row>
                <Col md={6}>
                  <h6>Metric Definitions:</h6>
                  <ul className="small">
                    <li><strong>Precision:</strong> Correct predictions / (Correct + False Positives)</li>
                    <li><strong>Recall:</strong> Correct predictions / (Correct + False Negatives)</li>
                    <li><strong>F1 Score:</strong> Harmonic mean of precision and recall</li>
                    <li><strong>Reward Score:</strong> RL feedback score (-2.0 to +1.0)</li>
                  </ul>
                </Col>
                <Col md={6}>
                  <h6>Feedback Types:</h6>
                  <ul className="small">
                    <li><strong>Confirmation:</strong> Model was correct (+reward)</li>
                    <li><strong>Correction:</strong> Model found field but wrong value (-reward)</li>
                    <li><strong>Addition:</strong> Model missed a field (-2.0 reward)</li>
                    <li><strong>Removal:</strong> Model found non-existent field (-reward)</li>
                  </ul>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Analytics;