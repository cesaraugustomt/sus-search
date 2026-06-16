## Estágio 1: build do React
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# VITE_API_URL vazio = usa caminhos relativos (/api/v1/...)
# O nginx do container proxy essas chamadas para o backend
# Para dev local sem Docker, defina VITE_API_URL=http://localhost:8000
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

## Estágio 2: nginx serve os estáticos e faz proxy para o backend
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
