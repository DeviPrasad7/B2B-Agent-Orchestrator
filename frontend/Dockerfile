# Base image for Node.js
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install Node dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Expose Vite's default development port
EXPOSE 5173

# Run the Vite development server and expose it to the host network
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
