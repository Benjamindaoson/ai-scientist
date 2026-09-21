"""Test Claude API connection with custom relay."""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_scientist.core.gateway import ClaudeRelayGateway

def test_api():
    """Test the Claude API connection."""
    print("=" * 60)
    print("Testing Claude API Connection (Relay Format)")
    print("=" * 60)

    # Force correct configuration (system env may have wrong values)
    os.environ["ANTHROPIC_API_KEY"] = "sk-CsvX9nQ2XsyZxF6nwR8uucvCUbfXN2hYp5CWD7tL6ECCdK1E"
    os.environ["ANTHROPIC_BASE_URL"] = "https://api.jingziai.club/v1"
    os.environ["DEFAULT_MODEL"] = "gpt-5.6-sol"

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    model = os.environ.get("DEFAULT_MODEL", "gpt-5.6-sol")

    print(f"\nConfiguration:")
    print(f"  API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")

    if not api_key or not base_url:
        print("\n❌ Missing API credentials!")
        return False

    print("\nTesting connection...")

    gateway = ClaudeRelayGateway(
        relay_url=base_url,
        api_key=api_key,
        model=model,
        max_tokens=100,
    )

    try:
        response = gateway.generate(
            "Reply with exactly one word: 'success'"
        )
        print(f"\n✅ API Connection Successful!")
        print(f"Response: {response.strip()}")
        return True
    except Exception as e:
        print(f"\n❌ API Connection Failed!")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
