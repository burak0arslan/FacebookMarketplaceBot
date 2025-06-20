"""
Llama AI Service for Facebook Marketplace Bot
Handles AI response generation using local Llama server
"""

import time
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import Config
from models.message import Message
from models.product import Product
from utils.logger import get_logger, log_ai_interaction


class LlamaAI:
    """
    AI service for generating intelligent responses to customer messages

    Features:
    - Local Llama server integration
    - Context-aware response generation
    - Product knowledge integration
    - Response quality validation
    - Conversation memory
    """

    def __init__(self, server_url: str = None, model_name: str = None):
        """
        Initialize Llama AI service

        Args:
            server_url: Ollama server URL (uses config default if None)
            model_name: Model name to use (uses config default if None)
        """
        self.server_url = server_url or Config.LLAMA_SERVER_URL
        self.model_name = model_name or Config.LLAMA_MODEL_NAME
        self.logger = get_logger(__name__)

        # AI generation settings
        self.temperature = Config.LLAMA_TEMPERATURE
        self.max_tokens = Config.LLAMA_MAX_TOKENS
        self.top_p = Config.LLAMA_TOP_P

        # Response tracking
        self.responses_generated = 0
        self.total_response_time = 0
        self.failed_generations = 0

        # Conversation memory
        self.conversation_history = {}

        self.logger.info(f"LlamaAI initialized - Server: {self.server_url}, Model: {self.model_name}")

    def test_connection(self) -> bool:
        """
        Test connection to Llama server

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("Testing Llama server connection...")

            response = requests.get(f"{self.server_url}/api/tags", timeout=5)

            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name', '') for model in models]

                self.logger.info(f"✅ Llama server connected successfully")
                self.logger.info(f"Available models: {model_names}")

                # Check if our model is available
                if any(self.model_name in name for name in model_names):
                    self.logger.info(f"✅ Model '{self.model_name}' is available")
                    return True
                else:
                    self.logger.warning(f"⚠️ Model '{self.model_name}' not found")
                    self.logger.info(f"Available models: {model_names}")
                    return False
            else:
                self.logger.error(f"❌ Server responded with status {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            self.logger.error("❌ Cannot connect to Llama server")
            self.logger.info("Make sure Ollama is running: 'ollama serve'")
            return False
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            return False

    def generate_response(self, message: Message, product: Optional[Product] = None,
                          conversation_context: List[Message] = None) -> Optional[str]:
        """
        Generate AI response to a customer message

        Args:
            message: Customer message to respond to
            product: Product being discussed (optional)
            conversation_context: Previous messages in conversation

        Returns:
            Generated response string or None if failed
        """
        start_time = time.time()

        try:
            self.logger.info(f"Generating AI response for message from {message.sender_name}")

            # Build context prompt
            prompt = self._build_prompt(message, product, conversation_context)

            # Generate response
            response = self._call_llama_api(prompt)

            if response:
                # Calculate timing and confidence
                response_time = time.time() - start_time
                confidence = self._calculate_confidence(message, response)

                # Update statistics
                self.responses_generated += 1
                self.total_response_time += response_time

                # Log AI interaction
                log_ai_interaction(
                    len(prompt),
                    len(response),
                    confidence,
                    response_time
                )

                self.logger.info(f"✅ AI response generated in {response_time:.2f}s (confidence: {confidence:.2f})")
                return response
            else:
                self.failed_generations += 1
                self.logger.error("❌ Failed to generate AI response")
                return None

        except Exception as e:
            self.failed_generations += 1
            self.logger.error(f"❌ AI response generation error: {e}")
            return None

    def _build_prompt(self, message: Message, product: Optional[Product] = None,
                      conversation_context: List[Message] = None) -> str:
        """
        Build context-aware prompt for AI

        Args:
            message: Customer message
            product: Product information
            conversation_context: Previous messages

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # System prompt
        prompt_parts.append("""You are a helpful Facebook Marketplace seller assistant. You respond to customer messages professionally and helpfully. Keep responses concise (1-3 sentences), friendly, and natural.

GUIDELINES:
- Be polite and professional
- Answer questions directly
- Don't make up information you don't have
- If you can't answer, politely say so
- Use casual, friendly tone
- Don't use emojis excessively""")

        # Product context
        if product:
            prompt_parts.append(f"""
PRODUCT INFORMATION:
- Title: {product.title}
- Price: ${product.price}
- Category: {product.category}
- Condition: {product.condition}
- Description: {product.description}
- Location: {product.location}""")

        # Conversation history
        if conversation_context:
            prompt_parts.append("\nCONVERSATION HISTORY:")
            for msg in conversation_context[-3:]:  # Last 3 messages
                role = "Customer" if msg.message_type.value == "customer_inquiry" else "You"
                prompt_parts.append(f"{role}: {msg.content}")

        # Current message
        prompt_parts.append(f"\nCUSTOMER MESSAGE: {message.content}")
        prompt_parts.append("\nYOUR RESPONSE:")

        return "\n".join(prompt_parts)

    def _call_llama_api(self, prompt: str) -> Optional[str]:
        """
        Call Llama API to generate response

        Args:
            prompt: Formatted prompt

        Returns:
            Generated response or None
        """
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": self.max_tokens
                }
            }

            response = requests.post(
                f"{self.server_url}/api/generate",
                json=payload,
                timeout=Config.LLAMA_API_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()

                if generated_text:
                    return self._clean_response(generated_text)
                else:
                    self.logger.warning("Empty response from Llama")
                    return None
            else:
                self.logger.error(f"Llama API error: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            self.logger.error("Llama API timeout")
            return None
        except Exception as e:
            self.logger.error(f"Llama API call error: {e}")
            return None

    def _clean_response(self, response: str) -> str:
        """
        Clean and validate AI response

        Args:
            response: Raw AI response

        Returns:
            Cleaned response
        """
        # Remove common AI artifacts
        response = response.replace("YOUR RESPONSE:", "").strip()
        response = response.replace("Response:", "").strip()

        # Split into sentences and take first few
        sentences = response.split('.')
        if len(sentences) > 3:
            response = '. '.join(sentences[:3]) + '.'

        # Ensure reasonable length
        if len(response) > 300:
            response = response[:300] + "..."

        return response

    def _calculate_confidence(self, message: Message, response: str) -> float:
        """
        Calculate confidence score for generated response

        Args:
            message: Original customer message
            response: Generated response

        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.7  # Base confidence

        # Boost confidence for questions with clear answers
        if message.contains_question and any(word in response.lower()
                                             for word in ['yes', 'no', 'available', 'price', '$']):
            confidence += 0.1

        # Reduce confidence for very short responses
        if len(response) < 20:
            confidence -= 0.1

        # Reduce confidence for very long responses
        if len(response) > 200:
            confidence -= 0.1

        # Boost confidence for price-related responses to price inquiries
        if message.contains_price_inquiry and '$' in response:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def get_fallback_response(self, message: Message) -> str:
        """
        Get fallback response when AI fails

        Args:
            message: Customer message

        Returns:
            Appropriate fallback response
        """
        if message.contains_price_inquiry:
            return "Thanks for your interest! The price is as listed, but feel free to ask if you have any other questions."

        elif message.contains_availability_inquiry:
            return "Yes, this item is still available! Let me know if you'd like to arrange pickup or have any questions."

        elif message.contains_question:
            return "Thanks for your message! I'll get back to you with more details soon."

        else:
            return "Thanks for your interest! Let me know if you have any questions."

    def add_conversation_context(self, conversation_id: str, message: Message):
        """
        Add message to conversation history

        Args:
            conversation_id: Conversation identifier
            message: Message to add
        """
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []

        self.conversation_history[conversation_id].append(message)

        # Keep only last 10 messages per conversation
        if len(self.conversation_history[conversation_id]) > 10:
            self.conversation_history[conversation_id] = self.conversation_history[conversation_id][-10:]

    def get_conversation_context(self, conversation_id: str) -> List[Message]:
        """
        Get conversation history

        Args:
            conversation_id: Conversation identifier

        Returns:
            List of previous messages
        """
        return self.conversation_history.get(conversation_id, [])

    def get_statistics(self) -> Dict[str, Any]:
        """Get AI service statistics"""
        avg_response_time = (self.total_response_time / self.responses_generated
                             if self.responses_generated > 0 else 0)

        success_rate = (self.responses_generated / (self.responses_generated + self.failed_generations) * 100
                        if (self.responses_generated + self.failed_generations) > 0 else 0)

        return {
            'responses_generated': self.responses_generated,
            'failed_generations': self.failed_generations,
            'success_rate': success_rate,
            'average_response_time': avg_response_time,
            'conversations_tracked': len(self.conversation_history)
        }


# Convenience functions
def create_llama_ai(server_url: str = None, model_name: str = None) -> LlamaAI:
    """
    Create and test Llama AI instance

    Args:
        server_url: Ollama server URL
        model_name: Model name

    Returns:
        LlamaAI instance

    Raises:
        Exception if connection fails
    """
    ai = LlamaAI(server_url, model_name)

    if not ai.test_connection():
        raise Exception("Failed to connect to Llama server")

    return ai


# Example usage and testing
if __name__ == "__main__":
    from utils.logger import setup_logging
    from models.message import Message
    from models.product import Product

    setup_logging()
    logger = get_logger(__name__)

    logger.info("Testing LlamaAI service...")

    try:
        # Test connection first
        ai = LlamaAI()

        if ai.test_connection():
            logger.info("✅ Llama connection successful")

            # Create test message
            test_message = Message.create_customer_message(
                "Hi! Is this iPhone still available? What's the lowest price?",
                "Test Customer",
                "conv_test_123"
            )

            # Create test product
            test_product = Product(
                title="iPhone 13 Pro - Excellent Condition",
                description="Barely used iPhone 13 Pro in excellent condition",
                price=650.0,
                category="Electronics",
                condition="Used - Like New"
            )

            # Generate response
            logger.info("Testing AI response generation...")
            response = ai.generate_response(test_message, test_product)

            if response:
                logger.info(f"✅ AI Response: {response}")

                # Test fallback
                fallback = ai.get_fallback_response(test_message)
                logger.info(f"✅ Fallback Response: {fallback}")

                # Show statistics
                stats = ai.get_statistics()
                logger.info(f"✅ AI Statistics: {stats}")

                logger.info("🎉 LlamaAI service test completed successfully!")
            else:
                logger.warning("⚠️ AI response generation failed - check your Llama setup")
        else:
            logger.error("❌ Llama connection failed")
            logger.info("Setup instructions:")
            logger.info("1. Install Ollama: https://ollama.ai")
            logger.info("2. Run: ollama pull llama2")
            logger.info("3. Run: ollama serve")

    except Exception as e:
        logger.error(f"LlamaAI test error: {e}")