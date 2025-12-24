# Node-based dev container for Vite React app
FROM node:20-alpine

WORKDIR /app

# Install deps first for better caching
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN if [ -f package-lock.json ]; then npm ci; \
    elif [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f pnpm-lock.yaml ]; then npm -g i pnpm && pnpm i --frozen-lockfile; \
    else npm i; fi

# Copy source
COPY . .

EXPOSE 5173

# Run Vite dev server bound to 0.0.0.0 for container access
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
