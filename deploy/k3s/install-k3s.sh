#!/bin/bash
set -e

echo "Installing K3s Server for FinansProtect on Mac Mini..."

# Disable Traefik during install if custom traefik configuration is needed later
# Install script from k3s.io
curl -sfL https://get.k3s.io | sh -s - server \
  --write-kubeconfig-mode 644 \
  --tls-san "api.finansprotect.bg" \
  --tls-san "app.finansprotect.bg"

echo "K3s installation complete. Waiting for nodes to be ready..."
sleep 10
kubectl get nodes

echo "Please save the token below to join agent nodes:"
sudo cat /var/lib/rancher/k3s/server/node-token
