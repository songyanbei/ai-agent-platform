import sys
import os
import json

# Add project root to path
sys.path.append("/Users/lyc/Desktop/s q/code/ai-agent-platform-main")

from shared.protocols.java_protocol import (
    build_invocation_declared,
    build_invocation_change_content,
    build_invocation_complete,
    InvocationType,
    StageStatus
)

def test_structure():
    print("Testing INVOCATION_DECLARED structure...")
    declared = build_invocation_declared(
        stage_id="test_stage",
        invocation_id="test_inv_id",
        name="test_name",
        invocation_type=InvocationType.SEARCH,
        render_type="STRUCTURED"
    )
    print(json.dumps(declared, indent=2, ensure_ascii=False))
    
    # Validation
    assert "invocation_id" in declared["context"], "invocation_id missing from context"
    assert "invocation_id" not in declared["messages"][0], "invocation_id SHOULD NOT be in messages"
    assert declared["messages"][0]["render_type"] == "STRUCTURED", "render_type missing from messages"

    print("\nTesting INVOCATION_CHANGE (Content Append)...")
    append = build_invocation_change_content(
        stage_id="test_stage",
        invocation_id="test_inv_id",
        content="test content",
        render_type="STRUCTURED"
    )
    print(json.dumps(append, indent=2, ensure_ascii=False))
    
    # Validation
    assert "invocation_id" in append["context"], "invocation_id missing from context"
    assert "invocation_id" not in append["messages"][0], "invocation_id SHOULD NOT be in messages"
    assert append["messages"][0]["render_type"] == "STRUCTURED", "render_type missing from messages"

    print("\nTesting INVOCATION_CHANGE (Complete)...")
    complete = build_invocation_complete(
        stage_id="test_stage",
        invocation_id="test_inv_id",
        content="final content",
        render_type="STRUCTURED"
    )
    print(json.dumps(complete, indent=2, ensure_ascii=False))
    
    # Validation
    assert "invocation_id" in complete["context"], "invocation_id missing from context"
    assert "invocation_id" not in complete["messages"][0], "invocation_id SHOULD NOT be in messages[0]"
    assert "invocation_id" not in complete["messages"][1], "invocation_id SHOULD NOT be in messages[1]"
    assert complete["messages"][1]["render_type"] == "STRUCTURED", "render_type missing from messages[1]"

    print("\n✅ All final tests passed!")

if __name__ == "__main__":
    test_structure()
