# AGenNext Code Assist Production Contract

Code Assist is the agent (requester/planner), not the enforcement point.

- AGenNext Runner is the runtime enforcement point.
- AGenNext Kernel is the infrastructure abstraction layer.
- AuthZEN is the decision interface.
- OpenFGA and OPA are compatibility metadata/backends usually behind Runner/AuthZEN.
- Agent ID Protocol is optional identity/governance context.
- ANP/ACP/Agent Client Protocol/A2A are configuration metadata, not direct clients in Code Assist.
- AGenNext Platform comes later and configures agents.
