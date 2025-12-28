import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { PLAN_LIMITS, getPlanFromRequest } from './config.js';
import { router as authRouter, authMiddleware } from './auth.js';

const app = express();
app.disable('x-powered-by');
app.use(helmet());
app.use(cors());
app.use(express.static('public'));
// Limit JSON and URL-encoded payload sizes to reduce abuse/DoS surface
app.use(express.json({ limit: '100kb' }));
app.use(express.urlencoded({ extended: false, limit: '50kb' }));
// Use simple query parser to avoid complex nested parsing
app.set('query parser', 'simple');

// Basic URL length guard to reduce ReDoS surface
app.use((req, res, next) => {
  const url = req.originalUrl || req.url || '';
  // Cap total URL length and path length separately
  if (url.length > 2048) {
    return res.status(414).send('URL too long');
  }
  const path = req.path || '';
  if (path.length > 1024) {
    return res.status(414).send('Path too long');
  }
  next();
});

// Plan-based rate limit (create limiters at init, select per request)
const planLimiters = Object.fromEntries(
  Object.entries(PLAN_LIMITS).map(([key, cfg]) => [
    key,
    rateLimit({ windowMs: cfg.windowMs, max: cfg.max })
  ])
);
app.use((req, res, next) => {
  const plan = getPlanFromRequest(req);
  const limiter = planLimiters[plan] || planLimiters.free;
  return limiter(req, res, next);
});

app.get('/api/v1/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Silence DevTools probe 404s
app.get('/.well-known/appspecific/com.chrome.devtools.json', (req, res) => {
  res.sendStatus(204);
});

// Auth routes
app.use('/api/v1/auth', authRouter);
app.get('/api/v1/users/me', authMiddleware, (req, res) => {
  res.json({ id: req.user.sub, email: req.user.email, role: req.user.role });
});

const port = process.env.PORT || 3001;

const host = '127.0.0.1';
const server = app.listen(port, host, () => {
  console.log(`Server running on http://${host}:${port}`);
});

server.on('error', (err) => {
  console.error('Server error:', err && (err.stack || err.message || err));
  process.exit(1);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err && (err.stack || err.message || err));
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection:', reason);
  process.exit(1);
});
