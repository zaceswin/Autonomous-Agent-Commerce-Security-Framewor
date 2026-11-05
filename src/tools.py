# tools.py
def execute_wallet_auth(method: str, args: dict, context: dict) -> str:
    """
    Bridges the agent's requested args with backend secure credentials.
    """
    amount = args.get("amount")
    merchant_id = args.get("merchant_id")
    
    # Extract secure backend context (Never exposed to the LLM)
    wallet = context.get("wallet")
    credential = context.get("credential")
    human_key = context.get("human_key")
    
    if not all([wallet, credential, human_key]):
        raise ValueError("Critical backend security context is missing.")

    auth_success, status_msg = wallet.authorize_transaction(
        amount=amount,
        merchant_id=merchant_id,
        credential=credential,
        human_key=human_key
    )
    return status_msg

TOOL_REGISTRY = {
    "wallet_authorize": execute_wallet_auth
}

def dispatch_tool(tool_name: str, method: str, args: dict, context: dict) -> str:
    """Routes the request to the correct python function."""
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{tool_name}' does not exist in the framework registry.")
    
    target_function = TOOL_REGISTRY[tool_name]
    return target_function(method, args, context)
