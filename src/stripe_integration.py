import stripe
from src.database import Database
from typing import Dict, Any
import os

class StripeIntegration:
    def __init__(self, db: Database):
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        self.db = db

    def create_subscription(self, user_id: int, price_id: str) -> Dict[str, Any]:
        try:
            customer = stripe.Customer.create(
                metadata={"user_id": user_id}
            )
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price_id}]
            )
            return {"status": "success", "subscription_id": subscription.id}
        except stripe.error.StripeError as e:
            print(f"Stripe error: {str(e)}")
            return {"status": "error", "message": str(e)}
