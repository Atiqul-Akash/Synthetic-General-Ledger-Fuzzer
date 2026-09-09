"""Lightweight Mock SAP S/4HANA OData V4 Gateway container service."""

import hashlib
import http.server
import json
import socketserver
import sys

PORT = 8000


class SAPODataHandler(http.server.BaseHTTPRequestHandler):
    """Simulates SAP S/4HANA Journal Entry OData V4 service endpoints."""

    def do_GET(self):
        # Health check
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "UP", "service": "SAP_S4HANA_ODATA_GATEWAY_MOCK"}')
            return

        # CSRF Token Fetch
        csrf_header = self.headers.get("x-csrf-token", "").lower()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("x-csrf-token", "SAP_S4_MOCK_CSRF_TOKEN_LIVE_9988")
        self.end_headers()

        response = {
            "@odata.context": "$metadata#JournalEntry",
            "value": [
                {
                    "CompanyCode": "1000",
                    "AccountingDocument": "1000000001",
                    "FiscalYear": "2026",
                    "DocumentDate": "2026-03-15",
                    "PostingDate": "2026-03-15",
                    "AccountingDocumentType": "SA",
                    "TotalGrossAmountInTransacCrcy": "15000.00",
                    "TransactionCurrency": "USD",
                }
            ],
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        doc_hash = int(hashlib.md5(body).hexdigest()[:6], 16)
        doc_num = "1000" + str(doc_hash % 900000 + 100000)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response = {
            "@odata.context": "$metadata#JournalEntry/$entity",
            "CompanyCode": payload.get("CompanyCode", "1000"),
            "AccountingDocument": doc_num,
            "FiscalYear": payload.get("FiscalYear", "2026"),
            "Status": "POSTED_SUCCESS",
            "Message": "Accounting document posted successfully into SAP S/4HANA Universal Journal",
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        # Quiet logger
        pass


def run_server(port: int = PORT):
    with socketserver.TCPServer(("", port), SAPODataHandler) as httpd:
        print(f"Mock SAP S/4HANA Gateway listening on port {port}")
        httpd.serve_forever()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(p)
