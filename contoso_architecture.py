import subprocess, os
from diagrams import Diagram, Cluster, Edge
from diagrams.azure.compute import AppServices, FunctionApps
from diagrams.azure.network import ApplicationGateway, FrontDoors, NetworkSecurityGroupsClassic, Firewall, RouteTables
from diagrams.azure.database import SQLServers, SQLDatabases
from diagrams.azure.storage import StorageAccounts
from diagrams.azure.security import KeyVaults
from diagrams.azure.integration import ServiceBus
from diagrams.azure.analytics import LogAnalyticsWorkspaces
from diagrams.azure.devops import ApplicationInsights
from diagrams.onprem.client import Users
os.makedirs("diagrams",exist_ok=True)
graph_attr={"splines":"ortho","nodesep":"0.8","ranksep":"1.2","bgcolor":"white","pad":"0.5","compound":"true"}
with Diagram("Contoso Architecture",filename="diagrams/contoso_architecture",outformat=["png","dot"],show=False,direction="TB",graph_attr=graph_attr):
 users=Users("Users"); afd=FrontDoors("Azure Front Door")
 with Cluster("vnet-contoso-auea-001 (10.10.0.0/16)"):
  with Cluster("snet-frontend"):
   n1=NetworkSecurityGroupsClassic("NSG-Frontend"); agw=ApplicationGateway("Application Gateway (WAF)"); web=AppServices("Web App")
  with Cluster("snet-backend"):
   n2=NetworkSecurityGroupsClassic("NSG-Backend"); api=AppServices("Order API"); fn=FunctionApps("Function App"); bus=ServiceBus("Service Bus")
  with Cluster("snet-data"):
   n3=NetworkSecurityGroupsClassic("NSG-Data"); sqls=SQLServers("SQL Server"); sql=SQLDatabases("SQL DB"); storage=StorageAccounts("Storage"); kv=KeyVaults("Key Vault")
  fw=Firewall("Azure Firewall"); rt=RouteTables("Route Table")
 with Cluster("Monitoring"):
  law=LogAnalyticsWorkspaces("Log Analytics"); ai=ApplicationInsights("App Insights")
 users>>Edge(label="HTTPS")>>afd>>agw>>web; web>>api; api>>sql; api>>storage; fn>>bus>>sql; web>>kv; api>>kv; fn>>kv; sqls>>sql; web>>fw; api>>fw; fn>>fw; web>>law; api>>law; fn>>law; web>>ai
subprocess.run(["graphviz2drawio","diagrams/contoso_architecture.dot","-o","diagrams/contoso_architecture.drawio"],check=True)
