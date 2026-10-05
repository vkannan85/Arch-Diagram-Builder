# Architecture Studio V5

## Goal
Replace the fixed-coordinate V4 renderer with a model-driven professional Azure architecture renderer.

## Rendering principles
- Official Microsoft Azure SVG architecture icons only for Azure services.
- One canonical architecture model drives preview, PNG/SVG and editable Draw.io output.
- Automatic layout: containers, subnets, resources, spacing and orthogonal connector lanes.
- No invented CIDRs, IP addresses, resources or configuration.
- Explicit directional flows and clearly separated relationship labels.
- Responsive browser preview with pan/zoom/full-screen.
- Dynamic canvas height/width based on topology rather than a hard-coded two-spoke layout.
- Architecture review remains separate from requested architecture; recommendations such as UDRs must not silently appear as deployed resources.

## First acceptance topology
Hub-and-spoke with on-premises datacentre, ExpressRoute circuit, Hub-VNet, GatewaySubnet/ExpressRoute Gateway, AzureFirewallSubnet/Azure Firewall, Spoke1/Spoke2 workload subnets and Windows VMs.

## Acceptance criteria
1. On-premises -> ExpressRoute -> ExpressRoute Gateway flow is visually unambiguous.
2. Gateway and Firewall are peer resources/subnets inside the Hub; no direct Gateway -> Firewall flow is implied unless requested.
3. Spoke peerings use dedicated connector lanes and never cross labels/resources.
4. Gateway transit / forwarded traffic / remote gateway settings are presented as relationship metadata rather than cluttering the diagram.
5. Missing GatewaySubnet, AzureFirewallSubnet and on-premises CIDRs display as not specified.
6. Official Azure service icons retain aspect ratio and are not recolored, stretched, flipped or rotated.
7. Exported Draw.io remains editable and visually follows the browser preview.
8. Layout expands for additional spokes/resources without overlapping the footer or other containers.

Microsoft guidance reference: Azure Architecture Center official icon collection and Azure Well-Architected diagram guidance.