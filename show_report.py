import json
from pathlib import Path

report = json.loads(Path("runs/agent_demo/latest_report.json").read_text(encoding="utf-8"))
print("\n=== MULTI-AGENT OSINT | REAL RESULTS ===")
print("Target:", report["target"])
print("Status:", report["status"])
print("Documents:", report["documents"])
print("Decision:", report["review_decision"])
for i, item in enumerate(report["evidence"], 1):
    print(f"\n[{i}] {item[chr(102)+chr(97)+chr(99)+chr(116)]}")
    print("Evidence:", item["quote"])
    print("Source:", item["url"])
    print("Verification:", item["status"])
print("\n=== END OF REPORT ===")
