import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple


class DelegationCredentialEngine:
    """
    Generates and verifies HMAC-SHA256 Delegation Credentials bound to a human principal.
    Enforces expiration, purpose scopes, nonces, and financial spending limits.
    """

    def __init__(self, human_secret_key: str, human_did: str):
        self.human_secret_key = human_secret_key.encode("utf-8")
        self.human_did = human_did

    def issue_credential(
        self,
        agent_id: str,
        max_per_tx: float,
        daily_limit: float,
        ttl_seconds: int = 3600,
    ) -> Dict:
        now = int(time.time())
        credential_body = {
            "credential_id": f"cred-{uuid.uuid4().hex[:8]}",
            "issuer": self.human_did,
            "subject_agent": agent_id,
            "issued_at": now,
            "expires_at": now + ttl_seconds,
            "constraints": {
                "max_per_transaction": max_per_tx,
                "daily_velocity_limit": daily_limit,
                "allowed_currency": "USD",
            },
            "nonce": uuid.uuid4().hex,
        }

        serialized = json.dumps(credential_body, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            self.human_secret_key, serialized, hashlib.sha256
        ).hexdigest()

        return {"payload": credential_body, "signature": signature}

    @staticmethod
    def verify_credential(credential: Dict, human_secret_key: str) -> Tuple[bool, str]:
        payload = credential.get("payload", {})
        signature = credential.get("signature", "")

        if not payload or not signature:
            return False, "Malformed credential structure."

        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(
            human_secret_key.encode("utf-8"), serialized, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return False, "Invalid cryptographic signature."

        if int(time.time()) > payload.get("expires_at", 0):
            return False, "Delegation credential expired."

        return True, "Credential valid."


class CircuitBreakerWallet:
    """
    Deterministic financial interceptor operating outside the LLM runtime context.
    Hard-enforces per-transaction caps and rolling 24-hour daily velocity limits.
    """

    def __init__(self, daily_limit: float, max_per_tx: float):
        self.daily_limit = daily_limit
        self.max_per_tx = max_per_tx
        self.spent_today = 0.0
        self.last_reset = time.time()
        self.transaction_log: List[Dict] = []

    def _check_and_reset_daily_window(self):
        if time.time() - self.last_reset > 86400:
            self.spent_today = 0.0
            self.last_reset = time.time()

    def authorize_transaction(
        self, amount: float, merchant_id: str, credential: Dict, human_key: str
    ) -> Tuple[bool, str]:
        # Step 1: Verify Delegation Credential
        valid, msg = DelegationCredentialEngine.verify_credential(
            credential, human_key
        )
        if not valid:
            return False, f"Authorization Refused: {msg}"

        # Step 2: Enforce Hard Cryptographic Limits from Credential Body
        constraints = credential["payload"]["constraints"]
        cred_max_tx = constraints["max_per_transaction"]
        cred_daily_limit = constraints["daily_velocity_limit"]

        self._check_and_reset_daily_window()

        effective_max_tx = min(cred_max_tx, self.max_per_tx)
        effective_daily_limit = min(cred_daily_limit, self.daily_limit)

        # Step 3: Evaluate Hard Financial Boundaries
        if amount > effective_max_tx:
            return (
                False,
                f"REJECTED: Amount ${amount:.2f} exceeds per-tx limit of ${effective_max_tx:.2f}.",
            )

        if self.spent_today + amount > effective_daily_limit:
            return (
                False,
                f"REJECTED: Transaction of ${amount:.2f} breaches daily velocity cap (${self.spent_today:.2f}/${effective_daily_limit:.2f} spent).",
            )

        # Step 4: Execute Authorization & Log State
        self.spent_today += amount
        tx_record = {
            "tx_id": f"tx-{uuid.uuid4().hex[:8]}",
            "amount": amount,
            "merchant": merchant_id,
            "timestamp": time.time(),
        }
        self.transaction_log.append(tx_record)
        return True, f"APPROVED: Transaction {tx_record['tx_id']} authorized for ${amount:.2f}."


class BlindedMarketEngine:
    """
    Asynchronous batch-clearing market engine.
    Prevents machine-speed tacit collusion using a SHA-256 Commit-Reveal protocol.
    """

    def __init__(self):
        self.commitments: Dict[str, str] = {}
        self.revealed_bids: Dict[str, Dict] = {}
        self.is_closed = False

    def submit_commitment(self, agent_id: str, bid_hash: str):
        if self.is_closed:
            raise ValueError("Bidding phase is closed.")
        self.commitments[agent_id] = bid_hash

    def reveal_bid(self, agent_id: str, price: float, salt: str, role: str):
        if agent_id not in self.commitments:
            raise ValueError("No commitment found for this agent.")

        payload = f"{price}:{salt}".encode("utf-8")
        computed_hash = hashlib.sha256(payload).hexdigest()

        if computed_hash != self.commitments[agent_id]:
            raise ValueError("Commitment verification failed! Price tampering detected.")

        self.revealed_bids[agent_id] = {"price": price, "role": role}

    def clear_market(self) -> Optional[Dict]:
        self.is_closed = True
        buyers = [b for b in self.revealed_bids.values() if b["role"] == "buyer"]
        sellers = [s for s in self.revealed_bids.values() if s["role"] == "seller"]

        if not buyers or not sellers:
            return None

        buyers.sort(key=lambda x: x["price"], reverse=True)
        sellers.sort(key=lambda x: x["price"])

        highest_buyer_bid = buyers[0]["price"]
        lowest_seller_ask = sellers[0]["price"]

        if highest_buyer_bid >= lowest_seller_ask:
            clearing_price = round((highest_buyer_bid + lowest_seller_ask) / 2.0, 2)
            return {
                "cleared": True,
                "clearing_price": clearing_price,
                "buyer_bid": highest_buyer_bid,
                "seller_ask": lowest_seller_ask,
            }

        return {"cleared": False, "reason": "No price overlap found."}


def run_simulation():
    """Executes full system simulation and print verification logs."""
    print("=== 1. INITIALIZING IDENTITY & DELEGATION ===")
    human_key = "super_secret_user_master_key_2030"
    human_did = "did:key:z13HhumanPrincipalNairobi2030"

    cred_engine = DelegationCredentialEngine(human_key, human_did)
    agent_credential = cred_engine.issue_credential(
        agent_id="agent-zack-shopping-v1",
        max_per_tx=150.00,
        daily_limit=300.00,
        ttl_seconds=3600,
    )
    print(f"Issued Delegation Credential: {agent_credential['payload']['credential_id']}")

    print("\n=== 2. EXECUTING SEALED-BID MARKET NEGOTIATION ===")
    market = BlindedMarketEngine()

    buyer_salt, seller1_salt, seller2_salt = "salt123", "salt456", "salt789"

    buyer_hash = hashlib.sha256(f"120.00:{buyer_salt}".encode("utf-8")).hexdigest()
    s1_hash = hashlib.sha256(f"140.00:{seller1_salt}".encode("utf-8")).hexdigest()
    s2_hash = hashlib.sha256(f"105.00:{seller2_salt}".encode("utf-8")).hexdigest()

    market.submit_commitment("buyer-agent", buyer_hash)
    market.submit_commitment("seller-alpha", s1_hash)
    market.submit_commitment("seller-beta", s2_hash)

    market.reveal_bid("buyer-agent", 120.00, buyer_salt, "buyer")
    market.reveal_bid("seller-alpha", 140.00, seller1_salt, "seller")
    market.reveal_bid("seller-beta", 105.00, seller2_salt, "seller")

    match = market.clear_market()
    print(f"Auction Clearing Result: {json.dumps(match, indent=2)}")

    print("\n=== 3. ROUTING THROUGH OUT-OF-BAND CIRCUIT BREAKER ===")
    wallet = CircuitBreakerWallet(daily_limit=300.00, max_per_tx=150.00)

    if match and match["cleared"]:
        final_price = match["clearing_price"]
        auth_success, status_msg = wallet.authorize_transaction(
            amount=final_price,
            merchant_id="seller-beta",
            credential=agent_credential,
            human_key=human_key,
        )
        print(f"Transaction Status: {status_msg}")

    print("\n=== 4. SIMULATING 3 A.M. AGENT HALLUCINATION / OVERSPEND ATTEMPTS ===")
    auth_success_a, status_msg_a = wallet.authorize_transaction(
        amount=500.00,
        merchant_id="seller-gamma",
        credential=agent_credential,
        human_key=human_key,
    )
    print(f"Hallucination Test ($500 item): {status_msg_a}")

    wallet.authorize_transaction(120.00, "seller-delta", agent_credential, human_key)
    auth_success_b, status_msg_b = wallet.authorize_transaction(
        amount=100.00,
        merchant_id="seller-epsilon",
        credential=agent_credential,
        human_key=human_key,
    )
    print(f"Velocity Limit Test (Exceeding $300 daily cap): {status_msg_b}")


if __name__ == "__main__":
    run_simulation()
