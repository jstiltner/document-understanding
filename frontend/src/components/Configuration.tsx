import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Form, Button, Alert, Spinner, Badge } from 'react-bootstrap';
import { documentApi, LLMConfig } from '../services/api';

const Configuration: React.FC = () => {
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Form state
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({
    anthropic: '',
    openai: ''
  });

  useEffect(() => {
    loadConfiguration();
  }, []);

  const loadConfiguration = async () => {
    try {
      setLoading(true);
      setError(null);
      const configData = await documentApi.getLLMConfig();
      setConfig(configData);
      setSelectedProvider(configData.default_provider);
      
      // Set default model for selected provider
      const providerConfig = configData.providers[configData.default_provider];
      if (providerConfig && providerConfig.default_model) {
        setSelectedModel(providerConfig.default_model);
      } else if (providerConfig && providerConfig.models.length > 0) {
        setSelectedModel(providerConfig.models[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
    
    // Reset model selection when provider changes
    if (config && config.providers[provider]) {
      const providerConfig = config.providers[provider];
      if (providerConfig.default_model) {
        setSelectedModel(providerConfig.default_model);
      } else if (providerConfig.models.length > 0) {
        setSelectedModel(providerConfig.models[0]);
      }
    }
  };

  const handleApiKeyChange = (provider: string, value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [provider]: value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      // Here you would typically call an API to save the configuration
      // For now, we'll just simulate the save
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSuccess('Configuration saved successfully!');
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async (provider: string) => {
    try {
      // Here you would test the API connection
      // For now, we'll just simulate the test
      await new Promise(resolve => setTimeout(resolve, 500));
      setSuccess(`${provider} connection test successful!`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(`${provider} connection test failed`);
    }
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
    <div className="configuration fade-in">
      <Row className="mb-4">
        <Col>
          <h1>Configuration</h1>
          <p className="text-muted">Configure LLM providers and API settings</p>
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

      <Row>
        <Col lg={8}>
          <Card className="mb-4">
            <Card.Header>
              <Card.Title className="mb-0">LLM Provider Settings</Card.Title>
            </Card.Header>
            <Card.Body>
              <Form>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Default Provider</Form.Label>
                      <Form.Select
                        value={selectedProvider}
                        onChange={(e) => handleProviderChange(e.target.value)}
                      >
                        {config && Object.keys(config.providers).map(provider => (
                          <option key={provider} value={provider}>
                            {provider.charAt(0).toUpperCase() + provider.slice(1)}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Default Model</Form.Label>
                      <Form.Select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        disabled={!selectedProvider}
                      >
                        {config && selectedProvider && config.providers[selectedProvider]?.models.map(model => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>
              </Form>
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Header>
              <Card.Title className="mb-0">API Keys</Card.Title>
            </Card.Header>
            <Card.Body>
              <Form>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label className="d-flex justify-content-between align-items-center">
                        Anthropic API Key
                        <Badge bg={config?.providers.anthropic ? 'success' : 'secondary'}>
                          {config?.providers.anthropic ? 'Available' : 'Not Configured'}
                        </Badge>
                      </Form.Label>
                      <div className="d-flex gap-2">
                        <Form.Control
                          type="password"
                          placeholder="sk-ant-..."
                          value={apiKeys.anthropic}
                          onChange={(e) => handleApiKeyChange('anthropic', e.target.value)}
                        />
                        <Button
                          variant="outline-primary"
                          size="sm"
                          onClick={() => testConnection('anthropic')}
                          disabled={!apiKeys.anthropic}
                        >
                          Test
                        </Button>
                      </div>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label className="d-flex justify-content-between align-items-center">
                        OpenAI API Key
                        <Badge bg={config?.providers.openai ? 'success' : 'secondary'}>
                          {config?.providers.openai ? 'Available' : 'Not Configured'}
                        </Badge>
                      </Form.Label>
                      <div className="d-flex gap-2">
                        <Form.Control
                          type="password"
                          placeholder="sk-..."
                          value={apiKeys.openai}
                          onChange={(e) => handleApiKeyChange('openai', e.target.value)}
                        />
                        <Button
                          variant="outline-primary"
                          size="sm"
                          onClick={() => testConnection('openai')}
                          disabled={!apiKeys.openai}
                        >
                          Test
                        </Button>
                      </div>
                    </Form.Group>
                  </Col>
                </Row>
              </Form>
            </Card.Body>
          </Card>

          <Card>
            <Card.Header>
              <Card.Title className="mb-0">Processing Settings</Card.Title>
            </Card.Header>
            <Card.Body>
              <Form>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Minimum Confidence Threshold</Form.Label>
                      <Form.Range
                        min={0}
                        max={1}
                        step={0.1}
                        defaultValue={0.7}
                      />
                      <Form.Text className="text-muted">
                        Documents below this confidence level will require review
                      </Form.Text>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Required Fields Threshold</Form.Label>
                      <Form.Range
                        min={0}
                        max={1}
                        step={0.1}
                        defaultValue={0.8}
                      />
                      <Form.Text className="text-muted">
                        Minimum confidence for required fields
                      </Form.Text>
                    </Form.Group>
                  </Col>
                </Row>
              </Form>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={4}>
          <Card className="sticky-top" style={{ top: '20px' }}>
            <Card.Header>
              <Card.Title className="mb-0">Available Providers</Card.Title>
            </Card.Header>
            <Card.Body>
              {config && Object.entries(config.providers).map(([provider, providerConfig]) => (
                <div key={provider} className="mb-3 p-3 border rounded">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <h6 className="mb-0">{provider.charAt(0).toUpperCase() + provider.slice(1)}</h6>
                    <Badge bg={providerConfig.models.length > 0 ? 'success' : 'secondary'}>
                      {providerConfig.models.length} models
                    </Badge>
                  </div>
                  <div className="small text-muted">
                    {providerConfig.models.join(', ')}
                  </div>
                  {providerConfig.default_model && (
                    <div className="small">
                      <strong>Default:</strong> {providerConfig.default_model}
                    </div>
                  )}
                </div>
              ))}
            </Card.Body>
            <Card.Footer>
              <Button
                variant="primary"
                onClick={handleSave}
                disabled={saving}
                className="w-100"
              >
                {saving ? 'Saving...' : 'Save Configuration'}
              </Button>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Configuration;