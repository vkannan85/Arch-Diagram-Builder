# Architecture Diagram Builder — Video Workflow Recommendations

Source tutorial: `Create Professional Architecture Diagrams using AI for Free using Python and Github Copilot`

Video: https://youtu.be/m7EuZ7GhinE

## Objective

Use the tutorial workflow as the design reference for this application. The application should not try to draw directly from a short natural-language sentence. It should first interpret the requirement into a structured architecture definition, then generate Python, then render the diagram.

## Recommended pipeline

```text
Natural-language requirement
        ↓
Requirement Interpreter
        ↓
Structured Architecture Model
        ↓
Python Generator
        ↓
Python Diagrams library
        ↓
Graphviz
        ↓
PNG / editable Draw.io
```

## 1. Runtime requirements

The deployment environment must contain:

- Python
- `diagrams` Python package
- Graphviz system executable (`dot`)
- Graphviz Python dependencies where required
- Draw.io conversion/output support

Installing the Python package alone is not enough. The Graphviz binary must be installed in the Linux/container runtime.

## 2. Requirement interpretation

Natural language should be converted into a structured architecture model before Python generation.

Capture at minimum:

- Cloud provider
- Tenant / management group / subscription where relevant
- Regions
- VNets / networks
- Hub and spoke relationships
- Subnets
- Resource placement
- Application components
- Data services
- Security services
- Private endpoints
- Monitoring
- Connections / traffic flows
- Routing
- Layout preferences

Do not infer important connections silently when they can be derived from explicit requirements.

## 3. Architecture preview

Before rendering, display the interpreted architecture to the user.

Example:

```text
Azure Landing Zone
├── Hub VNet
│   ├── Azure Firewall
│   └── Bastion
├── Spoke VNet 01
│   ├── Application 01
│   └── Application 02
└── Spoke VNet 02
    ├── Application 01
    └── Application 02

Connections
Hub ↔ Spoke 01
Hub ↔ Spoke 02

Outbound traffic
Spokes → Firewall → Internet
```

The structured model should become the source used to generate Python.

## 4. Python generation

Generate Python using the `diagrams` library and Graphviz rather than hard-coding one example architecture.

Use `Diagram`, `Cluster`, cloud-provider resource icons and explicit `Edge` relationships.

Containers should represent hierarchy such as:

```text
Azure
└── VNet
    └── Subnet
        └── Resource
```

The generated Python must remain downloadable so it can be reviewed and run locally in VS Code.

## 5. Graphviz

Graphviz performs graph layout and rendering. The application should verify `dot` is available before attempting generation and expose a useful diagnostic when it is missing.

Recommended startup/health validation:

```bash
dot -V
```

## 6. Editable output

Support at least:

- PNG preview
- Generated Python
- Editable Draw.io

The tutorial additionally demonstrates Graphviz-to-Draw.io conversion. Prefer generating Draw.io from the same structured architecture model so hierarchy and relationships remain editable.

Visio can be added as an additional export path rather than pretending a Draw.io file is native VSDX.

## 7. Terraform and Bicep

Future input modes should include:

```text
Natural language → structured model
Terraform        → structured model
Bicep            → structured model
```

All three should then use the same Python/diagram rendering pipeline.

## 8. Contoso reference architecture

Use the tutorial's Contoso example as a regression/reference architecture. It includes concepts such as:

- Azure VNet
- Frontend subnet
- Backend subnet
- Data subnet
- Azure Firewall
- Front Door
- Application Gateway/WAF
- App Services
- Function App
- Service Bus
- Azure SQL
- Storage Account
- Key Vault
- Private Endpoints
- Log Analytics
- Application Insights

The reference demonstrates that good diagram generation requires resources, placement, relationships and layout — not only a list of Azure services.

## 9. Layout guidance

The architecture definition should be able to express approximate layout intent, for example:

```text
TOP
Users / Front Door
        ↓
Application Gateway
        ↓
MIDDLE
Web App → Backend API → Function / Service Bus
        ↓
BOTTOM
SQL / Storage / Key Vault
Firewall / Monitoring
```

Graphviz should handle final positioning while respecting hierarchy and direction.

## 10. Application implementation priority

1. Improve natural-language interpretation.
2. Produce a richer structured architecture JSON model.
3. Generate Python from that model.
4. Validate Graphviz runtime availability.
5. Render PNG reliably.
6. Generate editable Draw.io from the same model.
7. Add iterative requirement refinement.
8. Add Terraform/Bicep ingestion.
9. Add native Visio export later.

## Key design principle

**Do not generate the final diagram directly from the user's sentence.**

Use:

```text
Requirement → Architecture Model → Python → Graphviz → Diagram
```

This intermediate architecture model is the key layer that allows the portal to understand arbitrary architecture requirements instead of repeatedly producing a fixed template.
