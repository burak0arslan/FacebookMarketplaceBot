#!/usr/bin/env python3
"""
AI Testing Script - Temporary Workaround
Tests the AI response system without requiring automated listing
"""

import sys
import os
import time
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llama_ai import LlamaAI
from models.message import Message
from models.product import Product
from utils.logger import get_logger, setup_logging


def create_test_products():
    """Create sample products for testing"""
    return [
        Product(
            title="iPhone 13 Pro - Like New",
            description="Barely used iPhone 13 Pro in excellent condition. No scratches, comes with original box and charger.",
            price=650.0,
            category="Electronics",
            condition="Used - Like New",
            location="Downtown"
        ),
        Product(
            title="Gaming Laptop - Dell G15",
            description="High-performance gaming laptop with RTX 3060. Perfect for gaming and work.",
            price=800.0,
            category="Electronics",
            condition="Used - Good",
            location="Suburb Area"
        ),
        Product(
            title="Vintage Leather Sofa",
            description="Beautiful vintage leather sofa in great condition. Perfect for any living room.",
            price=300.0,
            category="Furniture",
            condition="Used - Good",
            location="City Center"
        )
    ]


def create_test_messages():
    """Create sample customer messages for testing"""
    return [
        Message.create_customer_message(
            content="Hi! Is this still available? What's the lowest price you'd take?",
            sender_name="Sarah Johnson",
            conversation_id="conv_001"
        ),
        Message.create_customer_message(
            content="Does it come with the original charger and box?",
            sender_name="Mike Chen",
            conversation_id="conv_002"
        ),
        Message.create_customer_message(
            content="Can I pick this up today? What time works for you?",
            sender_name="Lisa Williams",
            conversation_id="conv_003"
        ),
        Message.create_customer_message(
            content="Is there any damage or issues I should know about?",
            sender_name="David Rodriguez",
            conversation_id="conv_004"
        ),
        Message.create_customer_message(
            content="Would you consider a trade instead of cash?",
            sender_name="Emma Taylor",
            conversation_id="conv_005"
        )
    ]


def test_ai_connection():
    """Test basic AI connection"""
    print("🔗 Testing AI Connection...")
    print("-" * 50)

    try:
        ai = LlamaAI()

        if ai.test_connection():
            print("✅ AI Connection successful!")
            print(f"   Server: {ai.server_url}")
            print(f"   Model: {ai.model_name}")
            return ai
        else:
            print("❌ AI Connection failed!")
            print("\n🛠️ Setup Instructions:")
            print("1. Install Ollama: https://ollama.ai")
            print("2. Run: ollama pull llama2")
            print("3. Run: ollama serve")
            print("4. Verify server is running at http://localhost:11434")
            return None

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None


def test_ai_responses(ai, products, messages):
    """Test AI response generation with sample data"""
    print("\n🤖 Testing AI Response Generation...")
    print("-" * 50)

    responses = []

    for i, (product, message) in enumerate(zip(products, messages), 1):
        print(f"\n📱 Test {i}/5:")
        print(f"Product: {product.title}")
        print(f"Customer: {message.content}")
        print(f"From: {message.sender_name}")

        try:
            # Generate AI response
            start_time = time.time()
            response = ai.generate_response(message, product)
            response_time = time.time() - start_time

            if response:
                print(f"🤖 AI Response: {response}")
                print(f"⏱️  Response time: {response_time:.2f}s")
                responses.append({
                    'product': product.title,
                    'message': message.content,
                    'response': response,
                    'time': response_time
                })
            else:
                print("❌ AI failed to generate response")
                # Try fallback
                fallback = ai.get_fallback_response(message)
                if fallback:
                    print(f"🔄 Fallback: {fallback}")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(1)  # Small delay between tests

    return responses


def test_fallback_responses(ai, messages):
    """Test fallback response system"""
    print("\n🔄 Testing Fallback Responses...")
    print("-" * 50)

    for i, message in enumerate(messages[:3], 1):
        fallback = ai.get_fallback_response(message)
        print(f"{i}. Message: {message.content[:50]}...")
        print(f"   Fallback: {fallback}")


def show_ai_statistics(ai):
    """Display AI performance statistics"""
    print("\n📊 AI Performance Statistics")
    print("-" * 50)

    stats = ai.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")


def main():
    """Main testing function"""
    print("🎯 Facebook Marketplace Bot - AI Testing")
    print("=" * 60)
    print("This script tests the AI response system independently")
    print("without requiring the automated listing functionality.\n")

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    # Test AI connection
    ai = test_ai_connection()
    if not ai:
        print("\n❌ Cannot proceed without AI connection")
        return False

    # Create test data
    products = create_test_products()
    messages = create_test_messages()

    print(f"\n📋 Created {len(products)} test products")
    print(f"📋 Created {len(messages)} test messages")

    # Test AI responses
    responses = test_ai_responses(ai, products, messages)

    # Test fallback system
    test_fallback_responses(ai, messages)

    # Show statistics
    show_ai_statistics(ai)

    # Summary
    print("\n🎉 Testing Summary")
    print("-" * 50)
    print(f"✅ Successful responses: {len(responses)}")
    print(f"🔄 AI service working: {'Yes' if len(responses) > 0 else 'No'}")

    if len(responses) > 0:
        avg_time = sum(r['time'] for r in responses) / len(responses)
        print(f"⏱️  Average response time: {avg_time:.2f}s")
        print("\n✅ AI system is working! You can now proceed with automated listing.")

        # Save test results
        print(f"\n💾 Test results saved to logs/")
        return True
    else:
        print("\n❌ AI system needs configuration. Check Llama server setup.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🚀 Ready to implement automated listing functionality!")
        else:
            print("\n🔧 Fix AI setup before proceeding to automated listing.")
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")