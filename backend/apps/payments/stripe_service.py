import logging

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Centralized wrapper for all Stripe API operations."""

    @staticmethod
    def create_payment_intent(
        amount_cents: int,
        currency: str = "usd",
        metadata: dict = None,
        receipt_email: str = None,
        customer_id: str = None,
    ) -> stripe.PaymentIntent:
        if amount_cents <= 0:
            raise ValueError("Amount must be positive")

        params = {
            "amount": amount_cents,
            "currency": currency,
            "automatic_payment_methods": {"enabled": True},
            "statement_descriptor_suffix": "WiseStay",
        }
        if metadata:
            params["metadata"] = metadata
        if receipt_email:
            params["receipt_email"] = receipt_email
        if customer_id:
            params["customer"] = customer_id

        try:
            pi = stripe.PaymentIntent.create(**params)
            logger.info("PaymentIntent created: %s ($%.2f)", pi.id, amount_cents / 100)
            return pi
        except stripe.error.CardError as e:
            logger.warning("Card error creating PaymentIntent: %s", e.user_message)
            raise ValueError(f"Card error: {e.user_message}")
        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid Stripe request: %s", e)
            raise
        except stripe.error.APIConnectionError as e:
            logger.warning("Stripe connection error, retrying: %s", e)
            # Retry once
            try:
                return stripe.PaymentIntent.create(**params)
            except Exception:
                raise

    @staticmethod
    def retrieve_payment_intent(payment_intent_id: str) -> stripe.PaymentIntent:
        return stripe.PaymentIntent.retrieve(payment_intent_id)

    @staticmethod
    def cancel_payment_intent(payment_intent_id: str) -> stripe.PaymentIntent:
        try:
            pi = stripe.PaymentIntent.cancel(payment_intent_id)
            logger.info("PaymentIntent cancelled: %s", payment_intent_id)
            return pi
        except stripe.error.InvalidRequestError as e:
            if "cannot be canceled" in str(e).lower():
                logger.info("PaymentIntent %s already not cancellable", payment_intent_id)
                return stripe.PaymentIntent.retrieve(payment_intent_id)
            raise

    @staticmethod
    def create_refund(
        payment_intent_id: str,
        amount_cents: int = None,
        reason: str = "requested_by_customer",
    ) -> stripe.Refund:
        params = {
            "payment_intent": payment_intent_id,
            "reason": reason,
        }
        if amount_cents is not None:
            params["amount"] = amount_cents

        try:
            refund = stripe.Refund.create(**params)
            logger.info(
                "Refund created: %s for PI %s (amount=%s)",
                refund.id, payment_intent_id,
                f"${amount_cents / 100:.2f}" if amount_cents else "full",
            )
            return refund
        except stripe.error.InvalidRequestError as e:
            logger.error("Refund failed for %s: %s", payment_intent_id, e)
            raise

    @staticmethod
    def create_transfer(
        amount_cents: int,
        destination_account_id: str,
        metadata: dict = None,
    ) -> stripe.Transfer:
        if not destination_account_id:
            raise ValueError("Destination account ID is required")

        params = {
            "amount": amount_cents,
            "currency": "usd",
            "destination": destination_account_id,
        }
        if metadata:
            params["metadata"] = metadata

        try:
            transfer = stripe.Transfer.create(**params)
            logger.info(
                "Transfer created: %s → %s ($%.2f)",
                transfer.id, destination_account_id, amount_cents / 100,
            )
            return transfer
        except Exception as e:
            logger.error("Transfer failed to %s: %s", destination_account_id, e)
            raise

    @staticmethod
    def create_connect_account_link(
        owner_user_id: int,
        return_url: str,
        refresh_url: str,
    ) -> str:
        from apps.accounts.models import User

        user = User.objects.select_related("owner_profile").get(pk=owner_user_id)
        profile = user.owner_profile

        if not profile.stripe_account_id:
            account = stripe.Account.create(
                type="express",
                country="US",
                email=user.email,
                capabilities={
                    "transfers": {"requested": True},
                },
                metadata={"wisestay_user_id": str(owner_user_id)},
            )
            profile.stripe_account_id = account.id
            profile.save(update_fields=["stripe_account_id", "updated_at"])
            logger.info("Stripe Connect account created: %s for user %s", account.id, user.email)

        link = stripe.AccountLink.create(
            account=profile.stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return link.url

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
        )
        return event
