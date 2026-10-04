# Architecture Diagram Builder – Portal V4

## Goal
Natural-language architecture requirements -> structured model -> on-screen diagram -> downloadable PNG and editable Draw.io.

## Portal UX
- Requirement editor
- Generate Diagram action
- Large on-screen diagram preview
- Refinement input for iterative changes
- Architecture review panel
- Download PNG
- Download Draw.io
- Azure-first component support

## Rendering principle
PNG and Draw.io must be exports of the same structured architecture model. Do not use a generative image as the source of truth. This keeps topology, labels and connectivity consistent and makes Draw.io editable.

## Azure V1 component coverage
- Virtual Networks / hub and spokes
- Subnets
- Windows/Linux VMs
- Azure Firewall
- ExpressRoute Gateway
- ExpressRoute Circuit
- On-premises datacentre
- VNet peering
- CIDR labels
- Peering properties such as forwarded traffic, gateway transit and remote gateway

## Current repository
The existing Flask app already provides requirement interpretation, Graphviz PNG generation and Draw.io XML export. V4 should build on that rather than replacing the complete pipeline.

## Next implementation steps
1. Upgrade the requirement parser to preserve explicit names and CIDRs.
2. Add ExpressRoute Circuit, ExpressRoute Gateway, on-premises network and VM parsing.
3. Add a deterministic hub-and-spoke layout.
4. Add a modern two-pane portal UI.
5. Add `/refine` so a user can modify the current model without starting over.
6. Ensure PNG and Draw.io use the same model.
7. Add architecture validation/review messages.
8. Test using the supplied Hub-VNet / Spoke1-VNet / Spoke2-VNet requirement.

## Acceptance test
Input should render:
- Hub-VNet 10.0.0.0/16
- Azure Firewall
- ExpressRoute Gateway -> ExpressRoute Circuit -> On-Premises Datacentre
- Spoke1-VNet 10.1.0.0/16 -> subnet 10.1.1.0/24 -> VM01
- Spoke2-VNet 10.2.0.0/16 -> subnet 10.2.1.0/24 -> VM02
- Hub <-> both spokes via VNet peering
- allow forwarded traffic
- allow gateway transit
- use remote gateway in spokes
