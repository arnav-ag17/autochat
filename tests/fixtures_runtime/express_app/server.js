/**
 * Simple Express application for testing.
 */

const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.json({ message: 'Hello from Express!', status: 'ok' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', health: 'healthy' });
});

app.get('/api/message', (req, res) => {
  res.json({ message: 'Hello from Express API!', data: 'test' });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Express app listening on port ${port}`);
});
