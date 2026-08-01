#!/usr/bin/env python3
"""
Simple standalone E2E test for vLLM and Ollama integration.

This script tests the implementation without requiring pytest or external servers.
It uses mocked HTTP responses to verify the routing and client logic.

Usage:
    python3 tests/simple_e2e_test.py
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch


def test_vllm_model_detection():
    """Test vLLM model detection patterns."""
    print("🧪 Testing vLLM Model Detection...")
    
    # Import modules
    import src.ai.ai_router
    import src.ai.vllm_client
    import src.ai.github_models
    
    # Mock settings
    with patch("src.ai.ai_router.get_settings") as mock_settings:
        settings = MagicMock()
        settings.github_token = "test"
        settings.gemini_api_key = None
        settings.vllm_base_url = "http://localhost:8000/v1"
        settings.vllm_api_key = "test-key"
        settings.ollama_base_url = None
        mock_settings.return_value = settings
        
        with patch("src.ai.vllm_client.get_settings", return_value=settings):
            with patch("src.ai.vllm_client.AsyncOpenAI"):
                from src.ai.ai_router import AIRouter
                router = AIRouter()
                
                # Test vLLM detection
                test_cases = [
                    ("meta-llama/Llama-2-7b-chat-hf", True, "HuggingFace path"),
                    ("mistralai/Mistral-7B-Instruct-v0.2", True, "Mistral path"),
                    ("vllm:some-model", True, "Explicit vllm: prefix"),
                    ("gpt-4", False, "GitHub Models"),
                    ("gemini-2.0-flash", False, "Gemini"),
                    ("llama2", False, "Ollama simple name"),
                ]
                
                all_passed = True
                for model, expected, description in test_cases:
                    result = router._is_vllm_model(model)
                    status = "✅" if result == expected else "❌"
                    print(f"  {status} {model:40s} → {result:5} (expected {expected:5}) - {description}")
                    if result != expected:
                        all_passed = False
                
                if all_passed:
                    print("✅ vLLM model detection: PASSED\n")
                    return True
                else:
                    print("❌ vLLM model detection: FAILED\n")
                    return False


def test_ollama_model_detection():
    """Test Ollama model detection patterns."""
    print("🧪 Testing Ollama Model Detection...")
    
    # Mock settings
    with patch("src.ai.ai_router.get_settings") as mock_settings:
        settings = MagicMock()
        settings.github_token = "test"
        settings.gemini_api_key = None
        settings.vllm_base_url = None
        settings.ollama_base_url = "http://localhost:11434/v1"
        mock_settings.return_value = settings
        
        with patch("src.ai.ollama_client.get_settings", return_value=settings):
            with patch("src.ai.ollama_client.AsyncOpenAI"):
                from src.ai.ai_router import AIRouter
                router = AIRouter()
                
                # Test Ollama detection
                test_cases = [
                    ("llama2", True, "Simple llama2"),
                    ("llama2:7b", True, "Llama2 with tag"),
                    ("mistral", True, "Mistral"),
                    ("codellama", True, "CodeLlama"),
                    ("ollama:some-model", True, "Explicit ollama: prefix"),
                    ("gpt-4", False, "GitHub Models"),
                    ("meta-llama/Llama-2-7b-chat-hf", False, "HuggingFace path (vLLM)"),
                ]
                
                all_passed = True
                for model, expected, description in test_cases:
                    result = router._is_ollama_model(model)
                    status = "✅" if result == expected else "❌"
                    print(f"  {status} {model:40s} → {result:5} (expected {expected:5}) - {description}")
                    if result != expected:
                        all_passed = False
                
                if all_passed:
                    print("✅ Ollama model detection: PASSED\n")
                    return True
                else:
                    print("❌ Ollama model detection: FAILED\n")
                    return False


def test_prefix_stripping():
    """Test provider prefix stripping."""
    print("🧪 Testing Prefix Stripping...")
    
    # Mock settings
    with patch("src.ai.ai_router.get_settings") as mock_settings:
        settings = MagicMock()
        settings.github_token = "test"
        settings.gemini_api_key = None
        settings.vllm_base_url = "http://localhost:8000/v1"
        settings.vllm_api_key = "test-key"
        settings.ollama_base_url = "http://localhost:11434/v1"
        mock_settings.return_value = settings
        
        with patch("src.ai.vllm_client.get_settings", return_value=settings):
            with patch("src.ai.ollama_client.get_settings", return_value=settings):
                with patch("src.ai.vllm_client.AsyncOpenAI"):
                    with patch("src.ai.ollama_client.AsyncOpenAI"):
                        from src.ai.ai_router import AIRouter
                        router = AIRouter()
                        
                        # Test prefix stripping
                        test_cases = [
                            ("vllm:mistral", "mistral"),
                            ("vllm:llama2", "llama2"),
                            ("ollama:codellama", "codellama"),
                            ("ollama:mistral:7b", "mistral:7b"),
                            ("gpt-4", "gpt-4"),
                            ("meta-llama/Llama-2-7b-chat-hf", "meta-llama/Llama-2-7b-chat-hf"),
                        ]
                        
                        all_passed = True
                        for original, expected in test_cases:
                            result = router._strip_provider_prefix(original)
                            status = "✅" if result == expected else "❌"
                            print(f"  {status} '{original:40s}' → '{result:40s}' (expected '{expected}')")
                            if result != expected:
                                all_passed = False
                        
                        if all_passed:
                            print("✅ Prefix stripping: PASSED\n")
                            return True
                        else:
                            print("❌ Prefix stripping: FAILED\n")
                            return False


async def test_vllm_client_mock():
    """Test VLLMClient with mocked API."""
    print("🧪 Testing VLLMClient (Mocked)...")
    
    with patch("src.ai.vllm_client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.vllm_base_url = "http://localhost:8000/v1"
        settings.vllm_api_key = "test-key"
        mock_settings.return_value = settings
        
        with patch("src.ai.vllm_client.AsyncOpenAI") as mock_openai:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response from vLLM"
            mock_response.usage.total_tokens = 42
            
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Test
            from src.ai.vllm_client import VLLMClient
            client = VLLMClient()
            
            messages = [{"role": "user", "content": "Hello"}]
            content, tokens = await client.generate_response(
                messages=messages,
                model="meta-llama/Llama-2-7b-chat-hf",
            )
            
            if content == "Test response from vLLM" and tokens == 42:
                print("  ✅ generate_response returned correct content and tokens")
                print(f"     Content: {content}")
                print(f"     Tokens: {tokens}")
                print("✅ VLLMClient: PASSED\n")
                return True
            else:
                print(f"  ❌ Expected 'Test response from vLLM' / 42, got '{content}' / {tokens}")
                print("❌ VLLMClient: FAILED\n")
                return False


async def test_ollama_client_mock():
    """Test OllamaClient with mocked API."""
    print("🧪 Testing OllamaClient (Mocked)...")
    
    with patch("src.ai.ollama_client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ollama_base_url = "http://localhost:11434/v1"
        mock_settings.return_value = settings
        
        with patch("src.ai.ollama_client.AsyncOpenAI") as mock_openai:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response from Ollama"
            mock_response.usage.total_tokens = 37
            
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Test
            from src.ai.ollama_client import OllamaClient
            client = OllamaClient()
            
            messages = [{"role": "user", "content": "Hello"}]
            content, tokens = await client.generate_response(
                messages=messages,
                model="llama2",
            )
            
            if content == "Test response from Ollama" and tokens == 37:
                print("  ✅ generate_response returned correct content and tokens")
                print(f"     Content: {content}")
                print(f"     Tokens: {tokens}")
                print("✅ OllamaClient: PASSED\n")
                return True
            else:
                print(f"  ❌ Expected 'Test response from Ollama' / 37, got '{content}' / {tokens}")
                print("❌ OllamaClient: FAILED\n")
                return False


async def test_router_dispatch():
    """Test AIRouter dispatches correctly to backends."""
    print("🧪 Testing AIRouter Dispatch...")
    
    with patch("src.ai.ai_router.get_settings") as mock_settings:
        settings = MagicMock()
        settings.github_token = "test"
        settings.gemini_api_key = None
        settings.vllm_base_url = "http://localhost:8000/v1"
        settings.vllm_api_key = "test-key"
        settings.ollama_base_url = "http://localhost:11434/v1"
        mock_settings.return_value = settings
        
        with patch("src.ai.github_models.AsyncOpenAI"):
            with patch("src.ai.vllm_client.get_settings", return_value=settings):
                with patch("src.ai.ollama_client.get_settings", return_value=settings):
                    with patch("src.ai.vllm_client.AsyncOpenAI") as mock_vllm:
                        with patch("src.ai.ollama_client.AsyncOpenAI") as mock_ollama:
                            # Setup mock vLLM response
                            vllm_response = MagicMock()
                            vllm_response.choices = [MagicMock()]
                            vllm_response.choices[0].message.content = "Response from vLLM"
                            vllm_response.usage.total_tokens = 20
                            
                            vllm_client = AsyncMock()
                            vllm_client.chat.completions.create = AsyncMock(return_value=vllm_response)
                            mock_vllm.return_value = vllm_client
                            
                            # Setup mock Ollama response
                            ollama_response = MagicMock()
                            ollama_response.choices = [MagicMock()]
                            ollama_response.choices[0].message.content = "Response from Ollama"
                            ollama_response.usage.total_tokens = 15
                            
                            ollama_client = AsyncMock()
                            ollama_client.chat.completions.create = AsyncMock(return_value=ollama_response)
                            mock_ollama.return_value = ollama_client
                            
                            # Test
                            from src.ai.ai_router import AIRouter
                            router = AIRouter()
                            
                            messages = [{"role": "user", "content": "Test"}]
                            
                            # Test vLLM routing
                            content1, tokens1 = await router.generate_response(
                                messages=messages,
                                model="meta-llama/Llama-2-7b-chat-hf",
                            )
                            
                            vllm_ok = content1 == "Response from vLLM" and tokens1 == 20
                            status1 = "✅" if vllm_ok else "❌"
                            print(f"  {status1} vLLM routing: {content1} ({tokens1} tokens)")
                            
                            # Test Ollama routing
                            content2, tokens2 = await router.generate_response(
                                messages=messages,
                                model="llama2",
                            )
                            
                            ollama_ok = content2 == "Response from Ollama" and tokens2 == 15
                            status2 = "✅" if ollama_ok else "❌"
                            print(f"  {status2} Ollama routing: {content2} ({tokens2} tokens)")
                            
                            if vllm_ok and ollama_ok:
                                print("✅ AIRouter dispatch: PASSED\n")
                                return True
                            else:
                                print("❌ AIRouter dispatch: FAILED\n")
                                return False


async def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 vLLM and Ollama Integration - Simple E2E Tests")
    print("=" * 70)
    print()
    
    # Add src to path
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    results = []
    
    # Synchronous tests
    results.append(test_vllm_model_detection())
    results.append(test_ollama_model_detection())
    results.append(test_prefix_stripping())
    
    # Async tests
    results.append(await test_vllm_client_mock())
    results.append(await test_ollama_client_mock())
    results.append(await test_router_dispatch())
    
    # Summary
    print("=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    
    print(f"\nTotal: {total} tests")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    
    if passed == total:
        print("\n🎉 All tests PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
