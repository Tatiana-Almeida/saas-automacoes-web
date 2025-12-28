const DEFAULT_SECRET = 'dev-secret-change-me';
export const JWT_SECRET = process.env.JWT_SECRET || DEFAULT_SECRET;
export const TOKEN_TTL = process.env.TOKEN_TTL || '1h';

export const PLAN_LIMITS = {
  free: { windowMs: 60_000, max: 60 },
  pro: { windowMs: 60_000, max: 600 },
  enterprise: { windowMs: 60_000, max: 3000 }
};

export function getPlanFromRequest(req) {
  return (req.headers['x-plan'] || 'free').toString().toLowerCase();
}

// Basic runtime safeguard
if (process.env.NODE_ENV === 'production' && JWT_SECRET === DEFAULT_SECRET) {
  // eslint-disable-next-line no-console
  console.error('FATAL: JWT_SECRET must be set in production');
  process.exit(1);
}
