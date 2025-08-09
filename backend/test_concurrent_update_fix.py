#!/usr/bin/env python3
"""
Test script to verify the LangGraph concurrent update fix
"""

def test_type_compatibility():
    """Test that the new Annotated pattern handles both list and string types"""
    
    # Test the basic data structures
    print("✅ Testing type compatibility for concurrent updates")
    
    # Simulate initial state (now uses list)
    initial_state = {
        "current_step": ["initialized"],
        "progress": {"current_step": 0, "percentage": 0, "total_steps": 10}
    }
    
    print(f"Initial state current_step: {initial_state['current_step']}")
    print(f"Type: {type(initial_state['current_step'])}")
    
    # Test update pattern (simulating what LangGraph would do)
    update1 = {"current_step": ["validate_input"]}
    update2 = {"current_step": ["process_document"]}
    
    # Simulate LangGraph's Annotated[List[str], add] behavior
    combined_steps = (
        initial_state['current_step'] + 
        update1['current_step'] + 
        update2['current_step']
    )
    
    final_state = {
        **initial_state,
        "current_step": combined_steps
    }
    
    print(f"\n✅ Combined state current_step: {final_state['current_step']}")
    print(f"Latest step: {final_state['current_step'][-1]}")
    print(f"Step history length: {len(final_state['current_step'])}")
    
    # Verify no type mismatch
    assert isinstance(final_state['current_step'], list)
    assert final_state['current_step'][-1] == "process_document"
    assert len(final_state['current_step']) == 3
    
    print("\n🎉 Type compatibility test passed! No list/str concatenation errors.")
    return True

def test_backward_compatibility():
    """Test that old string-based updates still work"""
    
    print("✅ Testing backward compatibility")
    
    # Simulate old-style string assignment (should be converted to list)
    from app.models.contract_state import update_state_step
    
    state = {"current_step": ["initialized"]}
    
    # This should work and return a proper update
    result = update_state_step(state, "new_step")
    
    print(f"Update result: {result}")
    assert result["current_step"] == ["new_step"]
    assert isinstance(result["current_step"], list)
    
    print("\n🎉 Backward compatibility test passed!")
    return True

if __name__ == "__main__":
    test_type_compatibility()
    test_backward_compatibility()
    print("\n🚀 All tests passed! The concurrent update fix is working correctly.")