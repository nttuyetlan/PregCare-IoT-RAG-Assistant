"""
Test suite for response validation functionality.
Verifies that hallucinated/off-topic responses are filtered.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import validate_response_content


def test_hallucinated_video_response():
    """Test that video creation response is filtered."""
    bad_response = (
        "Mầm Nhỏ rất tiếc vì đã không thể tiếp tục câu chuyện. "
        "Nhưng nếu bạn muốn, Mầm Nhỏ có thể giúp bạn tạo ra một đoạn video hấp dẫn "
        "cho kênh của mình. Bạn chỉ cần cung cấp cho Mầm Nhỏ một số thông tin về chủ đề "
        "và style video bạn muốn tạo. Mầm Nhỏ sẽ giúp bạn thực hiện dự án này."
    )
    
    result = validate_response_content(bad_response)
    expected = (
        "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. "
        "Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác nhất nhé."
    )
    
    assert result == expected, f"Expected validation to filter video response.\nGot: {result}"
    print("✅ test_hallucinated_video_response PASSED")


def test_hallucinated_subscribe_response():
    """Test that subscribe message is filtered."""
    bad_response = "Đã lâu, mọi người hãy subscribe cho kênh Ghiền Mì Gõ Để khô..."
    
    result = validate_response_content(bad_response)
    expected = (
        "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. "
        "Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác nhất nhé."
    )
    
    assert result == expected, f"Expected validation to filter subscribe response.\nGot: {result}"
    print("✅ test_hallucinated_subscribe_response PASSED")


def test_valid_response():
    """Test that valid medical responses pass through."""
    good_response = (
        "Dạ, trong tam cá nguyệt đầu, mẹ nên ăn đa dạng các loại thực phẩm "
        "bao gồm rau xanh, trái cây, thịt nạc và sữa để cung cấp đủ dinh dưỡng cho thai."
    )
    
    result = validate_response_content(good_response)
    assert result == good_response, f"Valid response should not be modified.\nGot: {result}"
    print("✅ test_valid_response PASSED")


def test_empty_response():
    """Test that empty responses are handled."""
    result = validate_response_content("")
    assert result == "", "Empty response should return empty"
    print("✅ test_empty_response PASSED")


def test_proper_no_info_response():
    """Test that the proper 'no information' response passes through."""
    proper_response = (
        "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. "
        "Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác nhất nhé."
    )
    
    result = validate_response_content(proper_response)
    assert result == proper_response, "Proper response should pass through unchanged"
    print("✅ test_proper_no_info_response PASSED")


if __name__ == "__main__":
    print("Running response validation tests...\n")
    
    try:
        test_hallucinated_video_response()
        test_hallucinated_subscribe_response()
        test_valid_response()
        test_empty_response()
        test_proper_no_info_response()
        
        print("\n✅ All tests PASSED!")
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
