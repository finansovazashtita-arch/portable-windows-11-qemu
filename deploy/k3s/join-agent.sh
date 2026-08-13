#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <K3S_URL> <K3S_TOKEN>"
    echo "Example: $0 https://192.168.1.100:6443 K10...token"
    exit 1
fi

K3S_URL=$1
K3S_TOKEN=$2

echo "Joining K3s cluster at $K3S_URL..."

curl -sfL https://get.k3s.io | K3S_URL=$K3S_URL K3S_TOKEN=$K3S_TOKEN sh -

echo "Node joined successfully. Check status from the server node."
