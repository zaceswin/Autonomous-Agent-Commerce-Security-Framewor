import pytest
from src.agent_commerce_security import (
    DelegationCredentialEngine,
    CircuitBreakerWallet,
    BlindedMarketEngine,
)


def test_credential_signature_verification():
    human_key = "secret123"
    engine = DelegationCredentialEngine(human_key, "did:key:123")
    cred = engine.issue_credential("agent1", max_per_tx=100, daily_limit=200)

    valid, msg = DelegationCredentialEngine.verify_credential(cred, human_key)
    assert valid is True
    assert msg == "Credential valid."


def test_invalid_credential_signature():
    human_key = "secret123"
    engine = DelegationCredentialEngine(human_key, "did:key:123")
    cred = engine.issue_credential("agent1", max_per_tx=100, daily_limit=200)

    valid, msg = DelegationCredentialEngine.verify_credential(cred, "wrong_key")
    assert valid is False
    assert "Invalid cryptographic signature" in msg


def test_circuit_breaker_per_tx_cap():
    human_key = "secret123"
    engine = DelegationCredentialEngine(human_key, "did:key:123")
    cred = engine.issue_credential("agent1", max_per_tx=150, daily_limit=300)

    wallet = CircuitBreakerWallet(daily_limit=300, max_per_tx=150)
    
    # Exceeding per-tx limit
    approved, msg = wallet.authorize_transaction(200.0, "merchantA", cred, human_key)
    assert approved is False
    assert "exceeds per-tx limit" in msg


def test_circuit_breaker_daily_velocity_limit():
    human_key = "secret123"
    engine = DelegationCredentialEngine(human_key, "did:key:123")
    cred = engine.issue_credential("agent1", max_per_tx=150, daily_limit=300)

    wallet = CircuitBreakerWallet(daily_limit=300, max_per_tx=150)
    
    # Authorized transaction 1 ($140)
    wallet.authorize_transaction(140.0, "merchantA", cred, human_key)
    # Authorized transaction 2 ($140) -> Total $280
    wallet.authorize_transaction(140.0, "merchantB", cred, human_key)

    # Transaction 3 ($50) -> Cumulative $330 exceeds $300 cap
    approved, msg = wallet.authorize_transaction(50.0, "merchantC", cred, human_key)
    assert approved is False
    assert "breaches daily velocity cap" in msg


def test_blinded_market_clearing():
    market = BlindedMarketEngine()
    import hashlib

    salt_buyer, salt_seller = "saltB", "saltS"
    b_hash = hashlib.sha256(f"120.0:{salt_buyer}".encode()).hexdigest()
    s_hash = hashlib.sha256(f"100.0:{salt_seller}".encode()).hexdigest()

    market.submit_commitment("buyer", b_hash)
    market.submit_commitment("seller", s_hash)

    market.reveal_bid("buyer", 120.0, salt_buyer, "buyer")
    market.reveal_bid("seller", 100.0, salt_seller, "seller")

    result = market.clear_market()
    assert result["cleared"] is True
    assert result["clearing_price"] == 110.0
