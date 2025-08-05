import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Form, Button, Alert, Table, Badge, Modal } from 'react-bootstrap';
import axios from 'axios';

interface FieldDefinition {
  id: number;
  name: string;
  display_name: string;
  description: string;
  field_type: string;
  is_required: boolean;
  validation_pattern?: string;
  extraction_hints?: any;
  is_active: boolean;
}

const FieldManagement: React.FC = () => {
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingField, setEditingField] = useState<FieldDefinition | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    field_type: 'text',
    is_required: false,
    validation_pattern: '',
    extraction_hints: {}
  });

  useEffect(() => {
    loadFields();
  }, []);

  const loadFields = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get('/fields');
      setFields(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load fields');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateField = () => {
    setEditingField(null);
    setFormData({
      name: '',
      display_name: '',
      description: '',
      field_type: 'text',
      is_required: false,
      validation_pattern: '',
      extraction_hints: {}
    });
    setShowModal(true);
  };

  const handleEditField = (field: FieldDefinition) => {
    setEditingField(field);
    setFormData({
      name: field.name,
      display_name: field.display_name,
      description: field.description,
      field_type: field.field_type,
      is_required: field.is_required,
      validation_pattern: field.validation_pattern || '',
      extraction_hints: field.extraction_hints || {}
    });
    setShowModal(true);
  };

  const handleSaveField = async () => {
    try {
      setError(null);
      
      if (editingField) {
        // Update existing field
        await axios.put(`/fields/${editingField.id}`, formData);
        setSuccess('Field updated successfully');
      } else {
        // Create new field
        await axios.post('/fields', formData);
        setSuccess('Field created successfully');
      }
      
      setShowModal(false);
      loadFields();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save field');
    }
  };

  const handleDeleteField = async (fieldId: number) => {
    if (!window.confirm('Are you sure you want to deactivate this field?')) {
      return;
    }

    try {
      setError(null);
      await axios.delete(`/fields/${fieldId}`);
      setSuccess('Field deactivated successfully');
      loadFields();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate field');
    }
  };

  const handleFormChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (loading) {
    return <div>Loading fields...</div>;
  }

  return (
    <div className="field-management">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h2>Field Management</h2>
            <Button variant="primary" onClick={handleCreateField}>
              Add New Field
            </Button>
          </div>
          <p className="text-muted">Configure extraction fields and their properties</p>
        </Col>
      </Row>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert variant="success" dismissible onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Card>
        <Card.Header>
          <Card.Title className="mb-0">Field Definitions</Card.Title>
        </Card.Header>
        <Card.Body>
          <Table striped hover responsive>
            <thead>
              <tr>
                <th>Display Name</th>
                <th>Internal Name</th>
                <th>Type</th>
                <th>Required</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field) => (
                <tr key={field.id}>
                  <td>
                    <strong>{field.display_name}</strong>
                  </td>
                  <td>
                    <code>{field.name}</code>
                  </td>
                  <td>
                    <Badge bg="info">{field.field_type}</Badge>
                  </td>
                  <td>
                    <Badge bg={field.is_required ? 'danger' : 'secondary'}>
                      {field.is_required ? 'Required' : 'Optional'}
                    </Badge>
                  </td>
                  <td>{field.description}</td>
                  <td>
                    <div className="d-flex gap-2">
                      <Button
                        size="sm"
                        variant="outline-primary"
                        onClick={() => handleEditField(field)}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="outline-danger"
                        onClick={() => handleDeleteField(field.id)}
                      >
                        Deactivate
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* Field Edit/Create Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            {editingField ? 'Edit Field' : 'Create New Field'}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Display Name *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => handleFormChange('display_name', e.target.value)}
                    placeholder="Patient First Name"
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Internal Name *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleFormChange('name', e.target.value)}
                    placeholder="patient_first_name"
                  />
                  <Form.Text className="text-muted">
                    Used internally (lowercase, underscores only)
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={formData.description}
                onChange={(e) => handleFormChange('description', e.target.value)}
                placeholder="Description of this field"
              />
            </Form.Group>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Field Type</Form.Label>
                  <Form.Select
                    value={formData.field_type}
                    onChange={(e) => handleFormChange('field_type', e.target.value)}
                  >
                    <option value="text">Text</option>
                    <option value="date">Date</option>
                    <option value="email">Email</option>
                    <option value="phone">Phone</option>
                    <option value="number">Number</option>
                  </Form.Select>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Check
                    type="checkbox"
                    label="Required Field"
                    checked={formData.is_required}
                    onChange={(e) => handleFormChange('is_required', e.target.checked)}
                  />
                  <Form.Text className="text-muted">
                    Required fields must be present for successful processing
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label>Validation Pattern (Regex)</Form.Label>
              <Form.Control
                type="text"
                value={formData.validation_pattern}
                onChange={(e) => handleFormChange('validation_pattern', e.target.value)}
                placeholder="^[A-Z0-9]{6,20}$"
              />
              <Form.Text className="text-muted">
                Optional regex pattern for field validation
              </Form.Text>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSaveField}>
            {editingField ? 'Update Field' : 'Create Field'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default FieldManagement;