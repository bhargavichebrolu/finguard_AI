# Production web image (Phase 6). Built with the repository root as context:
#   docker build -f docker/web/Dockerfile .
# Stage 1 builds the interface from source with the project's own build command (type check, then
# Vite). Stage 2 is Caddy serving those files over HTTPS and forwarding /api and /health to the
# API, so the browser sees one origin (ADR 0004). Both base images are pinned by digest.
FROM node:24.22.1-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM caddy:2-alpine@sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9

COPY --from=build /frontend/dist /srv
COPY docker/caddy/Caddyfile.production /etc/caddy/Caddyfile
