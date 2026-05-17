FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY --chmod=0444 go.mod go.sum ./
RUN go mod download
COPY --chmod=0444 main.go .
COPY --chmod=0555 internal ./internal
RUN CGO_ENABLED=0 GOOS=linux go build -o notification-service .

FROM alpine:3.20
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder --chmod=0555 /app/notification-service .
RUN addgroup -S revmine && adduser -S -G revmine revmine
USER revmine

EXPOSE 8005
CMD ["./notification-service"]
