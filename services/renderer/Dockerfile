FROM node:22-bookworm-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee
RUN apt-get update && apt-get install -y --no-install-recommends chromium ffmpeg fonts-dejavu-core ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/renderer
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts && npm cache clean --force
COPY src ./src
COPY render.mjs validate.mjs ./
ENV CHROME_PATH=/usr/bin/chromium NODE_ENV=production
USER 1000:1000
ENTRYPOINT ["node", "/opt/renderer/render.mjs"]
