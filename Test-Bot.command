#!/bin/bash
cd "$(dirname "$0")"
echo "==============================================="
echo "   Instagram Discord Bot - Manual Test"
echo "==============================================="
echo ""
.venv/bin/python3 test_send.py "https://discord.com/api/webhooks/1567518475306664019/fl5dkJQonwB_9CRBWkUmsVWlZD9EjDfn9v801PgSPTlzae8C1hqcfToUslQA4mJ9Iool"
echo ""
echo "Done! You can close this window."
read -n 1 -s -r -p "Press any key to exit..."

