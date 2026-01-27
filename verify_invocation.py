import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.abspath("/Users/lyc/Desktop/s q/code/ai-agent-platform-main"))

from shared.protocols.java_protocol import build_invocation_declared, InvocationType, StageStatus

def verify():
    msg = build_invocation_declared(
        stage_id="retrieval",
        invocation_id="test-inv-1",
        name="Test Query",
        invocation_type=InvocationType.SEARCH,
        status=StageStatus.RUNNING
    )
    
    print(json.dumps(msg, ensure_ascii=False, indent=2))
    
    # Assert check
    messages = msg.get("messages", [])
    if messages and "status" in messages[0]:
        print("\n✅ Verification SUCCESS: 'status' field found in message.")
        if messages[0]["status"] == "RUNNING":
             print("✅ Verification SUCCESS: 'status' value is 'RUNNING'.")
        else:
             print(f"❌ Verification FAILED: 'status' value is {messages[0]['status']}")
    else:
        print("\n❌ Verification FAILED: 'status' field NOT found in message.")

if __name__ == "__main__":
    verify()
