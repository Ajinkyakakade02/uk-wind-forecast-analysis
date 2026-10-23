FROM node:22-alpine

WORKDIR /app

# Copy package descriptors and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite development server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
