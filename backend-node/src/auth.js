import express from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { JWT_SECRET, TOKEN_TTL } from './config.js';

// In-memory users for demo purposes
// user = { id, email, passwordHash, role }
const users = new Map();
let idSeq = 1;

function sign(user) {
  return jwt.sign({ sub: user.id, email: user.email, role: user.role }, JWT_SECRET, { expiresIn: TOKEN_TTL });
}

export function authMiddleware(req, res, next) {
  const auth = req.headers.authorization || '';
  const [, token] = auth.split(' ');
  if (!token) return res.status(401).json({ error: 'missing_token' });
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;
    return next();
  } catch (e) {
    return res.status(401).json({ error: 'invalid_token' });
  }
}

export function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) return res.status(401).json({ error: 'unauthorized' });
    if (!roles.includes(req.user.role)) return res.status(403).json({ error: 'forbidden' });
    next();
  };
}

export const router = express.Router();

router.post('/register', async (req, res) => {
  const { email, password, role } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'email_password_required' });
  if (usersHasEmail(email)) return res.status(409).json({ error: 'email_in_use' });
  const passwordHash = await bcrypt.hash(password, 10);
  const user = { id: idSeq++, email, passwordHash, role: role === 'admin' ? 'admin' : 'viewer' };
  users.set(user.id, user);
  res.status(201).json({ id: user.id, email: user.email, role: user.role });
});

router.post('/login', async (req, res) => {
  const { email, password } = req.body || {};
  const user = findUserByEmail(email);
  if (!user) return res.status(401).json({ error: 'invalid_credentials' });
  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) return res.status(401).json({ error: 'invalid_credentials' });
  const token = sign(user);
  res.json({ token, user: { id: user.id, email: user.email, role: user.role } });
});

router.get('/me', authMiddleware, (req, res) => {
  res.json({ id: req.user.sub, email: req.user.email, role: req.user.role });
});

router.get('/admin/ping', authMiddleware, requireRole('admin'), (req, res) => {
  res.json({ ok: true, admin: true });
});

function usersHasEmail(email) {
  for (const u of users.values()) if (u.email === email) return true;
  return false;
}

function findUserByEmail(email) {
  for (const u of users.values()) if (u.email === email) return u;
  return null;
}
