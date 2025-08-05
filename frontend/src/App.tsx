import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Container, Navbar, Nav } from 'react-bootstrap';
import Dashboard from './components/Dashboard';
import DocumentReview from './components/DocumentReview';
import Configuration from './components/Configuration';
import Analytics from './components/Analytics';
import './App.css';

function App() {
  return (
    <div className="App">
      <Navbar bg="dark" variant="dark" expand="lg" className="mb-4">
        <Container>
          <Navbar.Brand href="/">Document Extraction Pipeline</Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link href="/">Dashboard</Nav.Link>
              <Nav.Link href="/analytics">Analytics</Nav.Link>
              <Nav.Link href="/config">Configuration</Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <Container>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/review/:documentId" element={<DocumentReview />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/config" element={<Configuration />} />
        </Routes>
      </Container>
    </div>
  );
}

export default App;