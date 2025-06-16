"""
Message Model for Facebook Marketplace Bot
This class represents customer messages and AI-generated responses
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """Types of messages in the system"""
    CUSTOMER_INQUIRY = "customer_inquiry"
    AI_RESPONSE = "ai_response"
    HUMAN_RESPONSE = "human_response"
    SYSTEM_MESSAGE = "system_message"


class MessageStatus(Enum):
    """Status of message processing"""
    NEW = "new"
    PROCESSING = "processing"
    RESPONDED = "responded"
    IGNORED = "ignored"
    ESCALATED = "escalated"
    ERROR = "error"


@dataclass
class Message:
    """
    Represents a message in the Facebook Marketplace conversation system

    Attributes:
        content: The actual message text
        sender_name: Name of the person who sent the message
        message_type: Type of message (customer, AI response, etc.)
        conversation_id: Unique identifier for the conversation thread
        product_title: Title of the product being discussed
        account_email: Email of the FB account receiving/sending the message
        timestamp: When the message was sent/received
        status: Current processing status of the message
        ai_confidence: Confidence score of AI-generated response (0-1)
        response_time: Time taken to generate response (seconds)
        contains_question: Whether the message contains a question
        contains_price_inquiry: Whether asking about price
        contains_availability_inquiry: Whether asking about availability
        requires_human_attention: Whether message needs human review
        sentiment: Detected sentiment (positive, negative, neutral)
        keywords: Extracted keywords from the message
        metadata: Additional data about the message
    """

    # Required fields
    content: str
    sender_name: str
    message_type: MessageType

    # Conversation context
    conversation_id: str = ""
    product_title: str = ""
    account_email: str = ""

    # Timing
    timestamp: Optional[str] = None

    # Processing status
    status: MessageStatus = MessageStatus.NEW

    # AI analysis fields
    ai_confidence: float = 0.0
    response_time: float = 0.0
    contains_question: bool = False
    contains_price_inquiry: bool = False
    contains_availability_inquiry: bool = False
    requires_human_attention: bool = False

    # Content analysis
    sentiment: str = "neutral"
    keywords: List[str] = field(default_factory=list)

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize and validate message data"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

        self._validate_data()
        self._analyze_content()

    def _validate_data(self):
        """Validate message data"""
        if not self.content or not self.content.strip():
            raise ValueError("Message content cannot be empty")

        if not self.sender_name or not self.sender_name.strip():
            raise ValueError("Sender name cannot be empty")

        if not isinstance(self.message_type, MessageType):
            raise ValueError("Invalid message type")

        if not isinstance(self.status, MessageStatus):
            raise ValueError("Invalid message status")

        if not 0 <= self.ai_confidence <= 1:
            raise ValueError("AI confidence must be between 0 and 1")

    def _analyze_content(self):
        """Analyze message content for patterns and keywords"""
        content_lower = self.content.lower()

        # Check for questions
        question_indicators = ['?', 'how', 'what', 'when', 'where', 'why', 'is this', 'can you', 'do you']
        self.contains_question = any(indicator in content_lower for indicator in question_indicators)

        # Check for price inquiries
        price_keywords = ['price', 'cost', 'how much', 'dollar', '$', 'cheap', 'expensive', 'negotiate', 'lower']
        self.contains_price_inquiry = any(keyword in content_lower for keyword in price_keywords)

        # Check for availability inquiries
        availability_keywords = ['available', 'still have', 'sold', 'pick up', 'when can', 'meet']
        self.contains_availability_inquiry = any(keyword in content_lower for keyword in availability_keywords)

        # Determine if human attention is needed
        human_attention_keywords = ['complaint', 'refund', 'problem', 'issue', 'broken', 'damaged', 'scam', 'police']
        self.requires_human_attention = any(keyword in content_lower for keyword in human_attention_keywords)

        # Extract basic keywords (simple approach)
        words = content_lower.split()
        # Filter out common words and short words
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of',
                      'as', 'by'}
        self.keywords = [word.strip('.,!?()[]') for word in words
                         if len(word) > 2 and word.lower() not in stop_words][:10]  # Limit to 10 keywords

    @classmethod
    def create_customer_message(cls, content: str, sender_name: str,
                                conversation_id: str = "", product_title: str = "",
                                account_email: str = "") -> 'Message':
        """
        Create a customer inquiry message

        Args:
            content: Message text from customer
            sender_name: Customer's name
            conversation_id: Conversation thread ID
            product_title: Product being discussed
            account_email: Account receiving the message

        Returns:
            Message instance for customer inquiry
        """
        return cls(
            content=content,
            sender_name=sender_name,
            message_type=MessageType.CUSTOMER_INQUIRY,
            conversation_id=conversation_id,
            product_title=product_title,
            account_email=account_email
        )

    @classmethod
    def create_ai_response(cls, content: str, conversation_id: str = "",
                           product_title: str = "", account_email: str = "",
                           ai_confidence: float = 0.0, response_time: float = 0.0) -> 'Message':
        """
        Create an AI-generated response message

        Args:
            content: AI-generated response text
            conversation_id: Conversation thread ID
            product_title: Product being discussed
            account_email: Account sending the response
            ai_confidence: AI confidence score
            response_time: Time taken to generate response

        Returns:
            Message instance for AI response
        """
        return cls(
            content=content,
            sender_name="AI Assistant",
            message_type=MessageType.AI_RESPONSE,
            conversation_id=conversation_id,
            product_title=product_title,
            account_email=account_email,
            ai_confidence=ai_confidence,
            response_time=response_time,
            status=MessageStatus.RESPONDED
        )

    def mark_as_processed(self) -> None:
        """Mark message as processed"""
        self.status = MessageStatus.RESPONDED

    def mark_as_ignored(self) -> None:
        """Mark message as ignored"""
        self.status = MessageStatus.IGNORED

    def mark_as_escalated(self) -> None:
        """Mark message as escalated to human"""
        self.status = MessageStatus.ESCALATED
        self.requires_human_attention = True

    def mark_as_error(self, error_info: str = "") -> None:
        """Mark message as having an error"""
        self.status = MessageStatus.ERROR
        if error_info:
            self.metadata['error'] = error_info

    def set_ai_analysis(self, confidence: float, response_time: float) -> None:
        """Set AI analysis results"""
        self.ai_confidence = max(0.0, min(1.0, confidence))
        self.response_time = max(0.0, response_time)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the message"""
        self.metadata[key] = value

    def get_age_minutes(self) -> float:
        """Get age of message in minutes"""
        if not self.timestamp:
            return 0.0

        try:
            msg_time = datetime.fromisoformat(self.timestamp)
            delta = datetime.now() - msg_time
            return delta.total_seconds() / 60
        except:
            return 0.0

    def get_priority_score(self) -> int:
        """
        Calculate priority score for message processing
        Higher score = higher priority
        """
        score = 0

        # Base priority for customer messages
        if self.message_type == MessageType.CUSTOMER_INQUIRY:
            score += 10

        # Higher priority for questions
        if self.contains_question:
            score += 5

        # Higher priority for price/availability inquiries
        if self.contains_price_inquiry or self.contains_availability_inquiry:
            score += 3

        # Highest priority for human attention needed
        if self.requires_human_attention:
            score += 20

        # Increase priority based on age (older messages get higher priority)
        age_hours = self.get_age_minutes() / 60
        if age_hours > 24:
            score += 10
        elif age_hours > 12:
            score += 5
        elif age_hours > 6:
            score += 2

        return score

    def is_urgent(self) -> bool:
        """Check if message needs urgent attention"""
        return (self.requires_human_attention or
                self.get_age_minutes() > 60 or  # Older than 1 hour
                self.get_priority_score() > 25)

    def get_short_content(self, max_length: int = 50) -> str:
        """Get truncated content for previews"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length - 3] + "..."

    def to_dict(self) -> Dict[str, Any]:
        """Convert Message to dictionary"""
        return {
            'content': self.content,
            'sender_name': self.sender_name,
            'message_type': self.message_type.value,
            'conversation_id': self.conversation_id,
            'product_title': self.product_title,
            'account_email': self.account_email,
            'timestamp': self.timestamp,
            'status': self.status.value,
            'ai_confidence': self.ai_confidence,
            'response_time': self.response_time,
            'contains_question': self.contains_question,
            'contains_price_inquiry': self.contains_price_inquiry,
            'contains_availability_inquiry': self.contains_availability_inquiry,
            'requires_human_attention': self.requires_human_attention,
            'sentiment': self.sentiment,
            'keywords': self.keywords,
            'metadata': self.metadata,
            'priority_score': self.get_priority_score(),
            'age_minutes': self.get_age_minutes()
        }

    def __str__(self) -> str:
        """String representation of Message"""
        return f"Message({self.message_type.value}, '{self.get_short_content()}', {self.sender_name})"

    def __repr__(self) -> str:
        """Detailed string representation of Message"""
        return (f"Message(type={self.message_type.value}, status={self.status.value}, "
                f"sender='{self.sender_name}', product='{self.product_title}', "
                f"priority={self.get_priority_score()})")


# Example usage and testing
if __name__ == "__main__":
    # Example 1: Customer inquiry message
    customer_msg = Message.create_customer_message(
        content="Hi, is this iPhone still available? What's the lowest price you can do?",
        sender_name="John Buyer",
        conversation_id="conv_123",
        product_title="iPhone 13 Pro",
        account_email="seller@gmail.com"
    )

    print("Customer Message:", customer_msg)
    print("Contains question:", customer_msg.contains_question)
    print("Contains price inquiry:", customer_msg.contains_price_inquiry)
    print("Keywords:", customer_msg.keywords)
    print("Priority score:", customer_msg.get_priority_score())
    print("Is urgent:", customer_msg.is_urgent())

    # Example 2: AI response message
    ai_msg = Message.create_ai_response(
        content="Yes, the iPhone is still available! The listed price is firm, but I can offer free shipping.",
        conversation_id="conv_123",
        product_title="iPhone 13 Pro",
        account_email="seller@gmail.com",
        ai_confidence=0.85,
        response_time=2.5
    )

    print("\nAI Response:", ai_msg)
    print("AI Confidence:", ai_msg.ai_confidence)
    print("Response time:", ai_msg.response_time, "seconds")

    # Example 3: Message requiring human attention
    urgent_msg = Message.create_customer_message(
        content="This product is broken and I want a refund! This is a scam!",
        sender_name="Angry Customer",
        product_title="iPhone 13 Pro"
    )

    print("\nUrgent Message:", urgent_msg)
    print("Requires human attention:", urgent_msg.requires_human_attention)
    print("Priority score:", urgent_msg.get_priority_score())
    print("Is urgent:", urgent_msg.is_urgent())