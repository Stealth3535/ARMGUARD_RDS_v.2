#!/bin/bash
# Generate self-signed SSL certificates for testing environment

SSL_DIR="$(dirname "$0")"

echo "Generating self-signed SSL certificates for ArmGuard testing..."

# Generate private key
openssl genrsa -out "$SSL_DIR/armguard.key" 2048

# Generate certificate signing request
openssl req -new -key "$SSL_DIR/armguard.key" -out "$SSL_DIR/armguard.csr" -subj "/C=PH/ST=Manila/L=Manila/O=ArmGuard/OU=Testing/CN=armguard.local"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in "$SSL_DIR/armguard.csr" -signkey "$SSL_DIR/armguard.key" -out "$SSL_DIR/armguard.crt" \
    -extfile <(printf "subjectAltName=DNS:armguard.local,DNS:localhost,IP:127.0.0.1")

# Set permissions
chmod 600 "$SSL_DIR/armguard.key"
chmod 644 "$SSL_DIR/armguard.crt"

# Clean up CSR
rm -f "$SSL_DIR/armguard.csr"

echo "SSL certificates generated successfully!"
echo "  Certificate: $SSL_DIR/armguard.crt"
echo "  Private Key: $SSL_DIR/armguard.key"
