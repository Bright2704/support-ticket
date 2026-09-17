# Frontend - Next.js
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build (optional - for production)
# RUN npm run build

# Expose port
EXPOSE 3000

# Run development server
CMD ["npm", "run", "dev"]
