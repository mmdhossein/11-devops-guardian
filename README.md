# 🛡️ DevOps Guardian

**Your AI co-pilot for safer infrastructure ops.**

Ever accidentally deleted a production pod at 3 AM? Or nervously triple-checked a kubectl command before hitting enter? DevOps Guardian is here to help. It's an AI agent that understands your intent, checks your permissions against clear policies, and pauses dangerous operations until a supervisor approves them with a one-time passcode.

Think of it as a senior engineer looking over your shoulder—minus the judgment, plus instant context on your Kubernetes clusters, ArgoCD apps, and Grafana dashboards.

---

## Why This Exists

Infrastructure work is stressful. One wrong command can take down services. Most teams rely on tribal knowledge, Slack approvals, or just hoping people don't mess up. DevOps Guardian makes safety systematic:

- **Natural language interface**: "Restart the payment-service pod in production" instead of memorizing kubectl syntax
- **Policy-driven access control**: Define roles and risk levels in a simple YAML file
- **Human-in-the-loop for risky ops**: High-risk actions automatically ping a supervisor for OTP approval
- **Full audit trail**: Every action logged with timestamps, risk levels, and approval chains

---

## What It Does

### For Engineers
- Ask questions in plain English: "Show me CPU usage for the API server"
- Execute safe operations instantly: listing pods, viewing dashboards, checking sync status
- Request approval for risky changes: scaling deployments, syncing ArgoCD apps, deleting resources

### For Supervisors
- Review pending approvals in a dedicated queue
- Approve or deny with TOTP (time-based one-time password)
- Browse a complete audit log of all system actions

### Supported Integrations
- **Kubernetes**: Pods, deployments, logs, scaling, restarts
- **ArgoCD**: App sync, rollback, history, deletion
- **Grafana**: Dashboards, metrics queries, alerts, datasources

---

## How It Works

1. **You say what you want**: "Scale the frontend deployment to 5 replicas"
2. **Agent parses intent**: Extracts action, resource type, and parameters
3. **Policy check**: Loads your role from `config/permissions.yaml` and determines risk level
4. **Approval flow**:
   - Low-risk → Executes immediately
   - Medium/High-risk → Supervisor gets pinged, action waits for OTP approval
5. **Execution & logging**: Action runs (or gets denied), full details saved to audit log

Under the hood: **LangGraph** orchestrates the workflow, **SQLite** stores sessions and logs, **pyotp** handles TOTP, and **Gradio** provides the UI.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt

### 2. Set Up Database
bash
python database_setup.py

This creates the SQLite database and seeds two admins:
- **alice** (engineer role) — TOTP secret: `JBSWY3DPEHPK3PXP`
- **bob** (supervisor role) — TOTP secret: `KVKFKRCPNZQUYMLX`

Use a TOTP app (Google Authenticator, Authy, 1Password) to generate OTP codes from these secrets.

### 3. Configure Policies
Edit `config/permissions.yaml` to define roles and what they can do:

yaml
roles:
  engineer:
kubernetes:
- action: get_pods
risk_level: low
- action: restart_pod
risk_level: medium
argocd:
- action: sync_application
risk_level: high

  supervisor:
kubernetes:
- action: "*"
risk_level: low

### 4. Set Environment Variables (Optional)
If you are connecting to real infrastructure, configure:

bash
export KUBECONFIG=/path/to/kubeconfig
export ARGOCD_SERVER=argocd.example.com
export ARGOCD_TOKEN=your-argocd-token
export GRAFANA_URL=https://grafana.example.com
export GRAFANA_API_KEY=your-grafana-key

**Note**: By default, tools return mock data for demo purposes. Check `tools/` to enable real API calls.

### 5. Launch the UI
bash
python app.py

Visit **http://localhost:7860** and login with `alice` or `bob` using their TOTP codes.

---

## Project Structure


devops-guardian/
├── config/
│   └── permissions.yaml          # Role-based access policies
├── core/
│   ├── auth.py                   # TOTP and session management
│   ├── database.py               # SQLite utilities
│   └── policy.py                 # Policy engine
├── tools/
│   ├── kubernetes.py             # K8s operations (MCP-style interface)
│   ├── argocd.py                 # ArgoCD operations
│   └── grafana.py                # Grafana operations
├── agent/
│   ├── state.py                  # LangGraph state definition
│   ├── nodes.py                  # Workflow nodes (parse, check, execute)
│   └── graph.py                  # LangGraph workflow assembly
├── database_setup.py             # Schema creation and seed data
├── app.py                        # Gradio UI
└── README.md

---

## Security Notes

- **TOTP secrets** are stored in plaintext in SQLite for demo purposes. In production, encrypt them or use a secret manager.
- **Sessions** expire after 24 hours by default (configurable in `core/auth.py`).
- **Audit logs** are append-only and include full action context for forensic review.
- **Tools** currently return mock data. Enable real API calls only in trusted environments with proper network isolation.

---

## Example Interactions

**Engineer (alice):**
- "Show me pods in the production namespace"
- "Get logs for the api-gateway pod"
- "Restart the cache pod" → *Supervisor approval required*

**Supervisor (bob):**
- Reviews pending approval: "alice wants to restart cache pod (risk: medium)"
- Provides OTP to approve
- Checks audit log to see all recent actions

---

## Customization

- **Add new tools**: Drop a new file in `tools/`, follow the MCP-style pattern (functions return `Dict[str, Any]` with `success`, `data`, `error`)
- **Extend policies**: Update `permissions.yaml` with new actions and risk levels
- **Tweak approval logic**: Modify `agent/nodes.py` to change when supervisor approval is required
- **Change UI colors**: Edit hex codes in `app.py` (currently Blue `#3B82F6`, Purple `#8B5CF6`)

---

## Roadmap

- [ ] Slack/Teams integration for approval notifications
- [ ] Multi-tenancy: separate policies per team/namespace
- [ ] LLM-powered intent parsing (currently rule-based)
- [ ] Real-time dashboard for pending approvals
- [ ] Export audit logs to S3/CloudWatch

---

## Contributing

This is a proof-of-concept built for teams tired of production anxiety. If you find it useful or have ideas, open an issue or PR. No formal guidelines yet—just keep it practical and well-documented.

---

## License

MIT. Use it, break it, fix it, ship it. Just don't blame us if you accidentally delete prod.

---

**Built with:** LangGraph, Gradio, SQLite, pyotp, and a healthy fear of `kubectl delete --all`.