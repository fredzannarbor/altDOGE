import stripe
import streamlit as st
from src.database import Database
import os

class WebhookHandler:
    def __init__(self, db: Database):
        self.db = db
        self.endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.endpoint_secret
            )
            if event["type"] == "customer.subscription.created":
                pass  # Update database
            return {"status": "success"}
        except ValueError as e:
            print(f"Webhook error: {str(e)}")
            return {"status": "error", "message": str(e)}
