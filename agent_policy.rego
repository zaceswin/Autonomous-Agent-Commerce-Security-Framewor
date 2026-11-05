package agent_policy

default allow = false

# Customer support agents can query orders but cannot modify them
allow {
    input.role == "customer_support"
    input.tool == "order_api"
    input.method == "GET"
}

# Admin agents have full privileges
allow {
    input.role == "admin_agent"
}

# Financial agents can post refunds, but only to the refund_api
allow {
    input.role == "finance_agent"
    input.tool == "refund_api"
    input.method == "POST"
}
