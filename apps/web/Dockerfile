# syntax=docker/dockerfile:1.7

FROM node:22.16.0-alpine3.21 AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci --workspace @kalibr-publisher/web --include-workspace-root

FROM base AS development
COPY apps/web ./apps/web
EXPOSE 3000
CMD ["npm", "run", "dev", "--workspace", "@kalibr-publisher/web", "--", "--hostname", "0.0.0.0"]

FROM base AS builder
COPY apps/web ./apps/web
ARG NEXT_PUBLIC_APP_NAME="Kalibr Publisher"
ARG NEXT_PUBLIC_DEFAULT_LOCALE="uz"
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME \
    NEXT_PUBLIC_DEFAULT_LOCALE=$NEXT_PUBLIC_DEFAULT_LOCALE
RUN npm run build --workspace @kalibr-publisher/web

FROM node:22.16.0-alpine3.21 AS production
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 10001 kalibr \
    && adduser --system --uid 10001 --ingroup kalibr kalibr

COPY --from=builder --chown=kalibr:kalibr /app/apps/web/.next/standalone ./
COPY --from=builder --chown=kalibr:kalibr /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=kalibr:kalibr /app/apps/web/public ./apps/web/public

USER kalibr
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
