FROM nikolaik/python-nodejs:python3.11-nodejs20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY prisma ./prisma/

# Install Node modules
RUN npm install
RUN npx prisma generate

# Copy Python requirements
COPY prediction-engine/requirements.txt ./prediction-engine/

# Install Python modules
RUN pip install --no-cache-dir -r prediction-engine/requirements.txt
RUN pip install statsbombpy catboost scikit-learn

# Copy all source code
COPY . .

# Build NestJS
RUN npm run build

# Add a startup script
RUN echo '#!/bin/bash\n\
# Start Python FastAPI in the background\n\
cd prediction-engine && uvicorn app.main:app --host 127.0.0.1 --port 8000 &\n\
\n\
# Go back to root and start NestJS\n\
cd /app\n\
# Run migrations before starting\n\
npx prisma db push --accept-data-loss\n\
npm run start:prod\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

# Expose NestJS port
EXPOSE 3000

# Start command
CMD ["/app/start.sh"]
