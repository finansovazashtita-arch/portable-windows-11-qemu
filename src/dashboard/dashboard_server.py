#!/usr/bin/env python3
"""
FinansProtect Web UI Dashboard Server & WebSockets Telemetry Hub (M65).

Serves the Web UI dashboard on port 8095, provides multi-entity compliance REST endpoints,
handles RFC 6455 WebSockets streaming for live NRA E-Invoicing status, PQC replication mesh telemetry,
and processes interactive audit corrections in real time.
"""

import base64
import hashlib
import http.server
import json
import logging
import os
import socket
import socketserver
import sys
import threading
import time
from typing import Any, Dict, Set

from src.dashboard.realtime_compliance_ui import (
    COMPLIANCE_ENGINE,
    RealTimeComplianceEngine,
    WebSocketFrame,
)

PORT = 8095
WEB_UI_DIR = os.path.join(os.path.dirname(__file__), "web_ui")

logger = logging.getLogger("dashboard_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Global registry of active WebSockets client sockets
CONNECTED_WS_LOCK = threading.Lock()
CONNECTED_WS_CLIENTS: Set[socket.socket] = set()


def broadcast_telemetry_frame():
    """Broadcast current compliance telemetry snapshot to all active WebSockets clients."""
    payload = COMPLIANCE_ENGINE.get_telemetry_payload()
    frame_bytes = WebSocketFrame.encode_text_frame(json.dumps(payload, ensure_ascii=False))

    with CONNECTED_WS_LOCK:
        dead_clients = set()
        for client_sock in CONNECTED_WS_CLIENTS:
            try:
                client_sock.sendall(frame_bytes)
            except Exception as e:
                logger.warning(f"Failed sending WS frame to client socket: {e}")
                dead_clients.add(client_sock)

        for dead in dead_clients:
            CONNECTED_WS_CLIENTS.remove(dead)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Multi-threaded HTTP server allowing simultaneous WebSocket streaming & HTTP requests."""
    daemon_threads = True
    allow_reuse_address = True


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_UI_DIR, **kwargs)

    def do_GET(self):
        # 1. Handle WebSockets Upgrade Handshake
        if self.path in ("/ws", "/ws/telemetry", "/ws/compliance") or (
            self.headers.get("Upgrade", "").lower() == "websocket"
        ):
            self._handle_websocket_upgrade()
            return

        # 2. REST API Telemetry Endpoints
        if self.path == "/api/telemetry":
            payload = COMPLIANCE_ENGINE.get_telemetry_payload()
            bg_entity = next((e for e in payload["entities"] if e["jurisdiction"] == "BG"), {})
            res_data = {
                "status": payload["system_status"],
                "overall_compliance_score": payload["overall_compliance_score"],
                "grand_total_debits": f"{payload['summary']['grand_total_debits_eur']:,.2f}",
                "grand_total_credits": f"{payload['summary']['grand_total_credits_eur']:,.2f}",
                "discrepancy": f"{payload['summary']['grand_total_discrepancy_eur']:,.2f} EUR",
                "audit_sha256": payload["summary"]["audit_ledger_hash_head"],
                "qemu_vm_status": "CONNECTED_127.0.0.1:5901",
                "infisical_vault": "CONNECTED",
                "n8n_automation": "ACTIVE",
                "entities_count": payload["summary"]["total_entities"],
                "nra_einvoice_count": len(payload["nra_einvoice_stream"]),
                "pqc_nodes_count": len(payload["pqc_replication_nodes"]),
            }
            self._send_json_response(res_data)
            return

        elif self.path in ("/api/compliance/telemetry", "/api/compliance/summary"):
            payload = COMPLIANCE_ENGINE.get_telemetry_payload()
            self._send_json_response(payload)
            return

        # 3. Server-Sent Events (SSE) Stream Fallback
        elif self.path in ("/api/compliance/stream", "/api/stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                for _ in range(5):
                    payload = COMPLIANCE_ENGINE.get_telemetry_payload()
                    data_str = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    self.wfile.write(data_str.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(1)
            except Exception:
                pass
            return

        # Default static web asset handler
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if self.path in ("/api/compliance/correct", "/api/correct"):
            res = COMPLIANCE_ENGINE.submit_correction(req_data)
            self._send_json_response(res, status=200 if res.get("success") else 400)
            if res.get("success"):
                broadcast_telemetry_frame()
            return

        elif self.path in ("/api/compliance/einvoice/submit", "/api/einvoice/submit"):
            res = COMPLIANCE_ENGINE.submit_nra_einvoice(req_data)
            self._send_json_response(res, status=200 if res.get("success") else 400)
            if res.get("success"):
                broadcast_telemetry_frame()
            return

        elif self.path in ("/api/compliance/mesh/sync", "/api/mesh/sync"):
            node_id = req_data.get("node_id", "hetzner-fsn1-dc14")
            res = COMPLIANCE_ENGINE.sync_pqc_mesh_node(node_id)
            self._send_json_response(res, status=200 if res.get("success") else 400)
            if res.get("success"):
                broadcast_telemetry_frame()
            return

        else:
            self.send_error(404, "Endpoint Not Found")

    def _send_json_response(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))

    def _handle_websocket_upgrade(self):
        ws_key = self.headers.get("Sec-WebSocket-Key")
        if not ws_key:
            self.send_error(400, "Missing Sec-WebSocket-Key header")
            return

        magic_guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        sha1_hash = hashlib.sha1((ws_key + magic_guid).encode("ascii")).digest()
        accept_key = base64.b64encode(sha1_hash).decode("ascii")

        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_key)
        self.end_headers()

        raw_socket = self.request
        with CONNECTED_WS_LOCK:
            CONNECTED_WS_CLIENTS.add(raw_socket)

        logger.info(f"🔌 WebSocket Client Connected from {self.client_address}")

        # Send initial state frame
        try:
            initial_payload = COMPLIANCE_ENGINE.get_telemetry_payload()
            raw_socket.sendall(
                WebSocketFrame.encode_text_frame(json.dumps(initial_payload, ensure_ascii=False))
            )
        except Exception as e:
            logger.warning(f"Error sending initial WS frame: {e}")

        # Read loop for incoming WS client frames
        buffer = bytearray()
        try:
            raw_socket.settimeout(30.0)
            while True:
                chunk = raw_socket.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)

                while buffer:
                    msg_text, consumed = WebSocketFrame.decode_client_frame(bytes(buffer))
                    if consumed == 0:
                        break
                    buffer = buffer[consumed:]

                    if msg_text:
                        self._process_ws_client_message(msg_text, raw_socket)
        except Exception as e:
            logger.debug(f"WS connection closed ({self.client_address}): {e}")
        finally:
            with CONNECTED_WS_LOCK:
                CONNECTED_WS_CLIENTS.discard(raw_socket)
            logger.info(f"🔌 WebSocket Client Disconnected from {self.client_address}")

    def _process_ws_client_message(self, msg_text: str, client_socket: socket.socket):
        try:
            msg = json.loads(msg_text)
            action = msg.get("action")

            if action == "correct_entry":
                res = COMPLIANCE_ENGINE.submit_correction(msg)
                broadcast_telemetry_frame()
            elif action == "submit_einvoice":
                res = COMPLIANCE_ENGINE.submit_nra_einvoice(msg)
                broadcast_telemetry_frame()
            elif action == "sync_pqc_node":
                node_id = msg.get("node_id", "hetzner-fsn1-dc14")
                res = COMPLIANCE_ENGINE.sync_pqc_mesh_node(node_id)
                broadcast_telemetry_frame()
            elif action == "ping":
                reply = {"type": "pong", "timestamp": time.time()}
                client_socket.sendall(WebSocketFrame.encode_text_frame(json.dumps(reply)))
        except Exception as e:
            logger.warning(f"Failed processing WS client message: {e}")


def main():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"🚀 FinansProtect Web UI Audit Dashboard & WebSockets Streamer running on http://0.0.0.0:{PORT}")
    print(f"📡 WebSockets endpoint live on ws://0.0.0.0:{PORT}/ws")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server.")
        server.server_close()


if __name__ == "__main__":
    main()
