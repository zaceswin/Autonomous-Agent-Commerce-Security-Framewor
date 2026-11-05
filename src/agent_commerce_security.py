# main.py
import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple

from observability import tool_execution_wrapper

class DelegationCredentialEngine:
    def __init__(self, human_secret_key: str, human_did: str):
        self.human_secret_key = human_secret_key.encode("utf-8")
        self.human_did = human_did

    def issue_credential(self, agent_id: str, max_per_tx: float, daily_limit: float, ttl_seconds: int = 3600) -> Dict:
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
        signature = hmac.new(self.human_secret_key, serialized, hashlib.sha256).hexdigest()
        return {"payload": credential_body, "signature": signature}

    @staticmethod
    def verify_credential(credential: Dict, human_secret_key: str) -> Tuple[bool, str]:
        payload = credential.get("payload", {})
        signature = credential.get("signature", "")
        if not payload or not signature:
            return False, "Malformed credential structure."
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(human_secret_key.encode("utf-8"), serialized, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return False, "Invalid cryptographic signature."
        if int(time.time()) > payload.get("expires_at", 0):
            return False, "Delegation credential expired."
        return True, "Credential valid."


class CircuitBreakerWallet:
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

    def authorize_transaction(self, amount: float, merchant_id: str, credential: Dict, human_key: str) -> Tuple[bool, str]:
        valid, msg = DelegationCredentialEngine.verify_credential(credential, human_key)
        if not valid:
            return False, f"Authorization Refused: {msg}"

        constraints = credential["payload"]["constraints"]
        effective_max_tx = min(constraints["max_per_transaction"], self.max_per_tx)
        effective_daily_limit = min(constraints["daily_velocity_limit"], self.daily_limit)

        self._check_and_reset_daily_window()

        if amount > effective_max_tx:
            return False, f"REJECTED: Amount ${amount:.2f} exceeds per-tx limit of ${effective_max_tx:.2f}."
        if self.spent_today + amount > effective_daily_limit:
            return False, f"REJECTED: Transaction of ${amount:.2f} breaches daily velocity cap (${self.spent_today:.2f}/${effective_daily_limit:.2f} spent)."

        self.spent_today += amount
        tx_record = {"tx_id": f"tx-{uuid.uuid4().hex[:8]}", "amount": amount, "merchant": merchant_id, "timestamp": time.time()}
        self.transaction_log.append(tx_record)
        return True, f"APPROVED: Transaction {tx_record['tx_id']} authorized for ${amount:.2f}."


class BlindedMarketEngine:
    def __init__(self):
        self.commitments: Dict[str, str] = {}
        self.revealed_bids: Dict[str, Dict] = {}
        self.is_closed = False

    def submit_commitment(self, agent_id: str, bid_hash: str):
        if self.is_closed: raise ValueError("Bidding phase is closed.")
        self.commitments[agent_id] = bid_hash

    def reveal_bid(self, agent_id: str, price: float, salt: str, role: str):
        if agent_id not in self.commitments: raise ValueError("No commitment found.")
        payload = f"{price}:{salt}".encode("utf-8")
        if hashlib.sha256(payload).hexdigest() != self.commitments[agent_id]:
            raise ValueError("Commitment verification failed! Price tampering detected.")
        self.revealed_bids[agent_id] = {"price": price, "role": role}

    def clear_market(self) -> Optional[Dict]:
        self.is_closed = True
        buyers = sorted([b for b in self.revealed_bids.values() if b["role"] == "buyer"], key=lambda x: x["price"], reverse=True)
        sellers = sorted([s for s in self.revealed_bids.values() if s["role"] == "seller"], key=lambda x: x["price"])
        
        if not buyers or not sellers: return None
        if buyers[0]["price"] >= sellers[0]["price"]:
            return {"cleared": True, "clearing_price": round((buyers[0]["price"] + sellers[0]["price"]) / 2.0, 2)}
        return {"cleared": False, "reason": "No price overlap found."}


def run_simulation():
    print("=== 1. INITIALIZING IDENTITY & DELEGATION ===")
    human_key = "super_secret_user_master_key_2030"
    human_did = "did:key:z13HhumanPrincipalNairobi2030"

    cred_engine = DelegationCredentialEngine(human_key, human_did)
    agent_credential = cred_engine.issue_credential("agent-zack-shopping-v1", max_per_tx=150.00, daily_limit=300.00)
    print(f"Issued Delegation Credential: {agent_credential['payload']['credential_id']}")

    print("\n=== 2. EXECUTING SEALED-BID MARKET NEGOTIATION ===")
    market = BlindedMarketEngine()
    buyer_salt, seller_salt = "salt123", "salt456"
    
    market.submit_commitment("buyer-agent", hashlib.sha256(f"120.00:{buyer_salt}".encode("utf-8")).hexdigest())
    market.submit_commitment("seller-beta", hashlib.sha256(f"105.00:{seller_salt}".encode("utf-8")).hexdigest())

    market.reveal_bid("buyer-agent", 120.00, buyer_salt, "buyer")
    market.reveal_bid("seller-beta", 105.00, seller_salt, "seller")

    match = market.clear_market()
    print(f"Auction Clearing Result: {json.dumps(match, indent=2)}")

    print("\n=== 3. ROUTING THROUGH OBSERVED CIRCUIT BREAKER ===")
    wallet = CircuitBreakerWallet(daily_limit=300.00, max_per_tx=150.00)
    
    # -------------------------------------------------------------
    # Context Injection: This securely passes backend state to tools.py 
    # without letting the LLM read or modify the human_key.
    # -------------------------------------------------------------
    backend_context = {
        "wallet": wallet,
        "credential": agent_credential,
        "human_key": human_key
    }

    # Mock token usage for telemetry tracking
    mock_llm_meta = {"prompt_tokens": 150, "completion_tokens": 25, "model": "gpt-4"}

    if match and match["cleared"]:
        agent_args = {"amount": match["clearing_price"], "merchant_id": "seller-beta"}
        
        status_msg = tool_execution_wrapper(
            tool_name="wallet_authorize",
            method="POST",
            args=agent_args,
            agent_role="shopping_agent",
            llm_response_metadata=mock_llm_meta,
            context=backend_context
        )
        print(f"Transaction Status (Telemetry Wrapped): {status_msg}")

    print("\n=== 4. SIMULATING 3 A.M. AGENT HALLUCINATION / OVERSPEND ATTEMPTS ===")
    
    hallucination_args = {"amount": 500.00, "merchant_id": "seller-gamma"}
    status_msg_a = tool_execution_wrapper(
        tool_name="wallet_authorize",
        method="POST",
        args=hallucination_args,
        agent_role="shopping_agent",
        llm_response_metadata=mock_llm_meta,
        context=backend_context
    )
    print(f"Hallucination Test ($500 item): {status_msg_a}")

if __name__ == "__main__":
    run_simulation()
