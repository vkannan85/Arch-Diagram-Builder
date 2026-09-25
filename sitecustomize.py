"""Runtime compatibility aliases for generated Diagrams code.

Python imports sitecustomize automatically at startup when it is on sys.path.
This keeps generated architecture scripts compatible with diagrams==0.24.4
while the generator is being migrated to the canonical Azure node names.
"""
import sys
import types

try:
    import diagrams.azure.network as network
    # diagrams.azure.network exposes ApplicationGateway (singular), while the
    # generator historically emitted ApplicationGateways.
    if not hasattr(network, "ApplicationGateways") and hasattr(network, "ApplicationGateway"):
        network.ApplicationGateways = network.ApplicationGateway
except Exception:
    pass

try:
    from diagrams.azure.monitor import LogAnalyticsWorkspaces
    # Older generator output imports this from azure.analytics. Provide a
    # narrow compatibility module so generated scripts continue to run.
    try:
        import diagrams.azure.analytics as analytics
    except Exception:
        analytics = types.ModuleType("diagrams.azure.analytics")
        sys.modules["diagrams.azure.analytics"] = analytics
    if not hasattr(analytics, "LogAnalyticsWorkspaces"):
        analytics.LogAnalyticsWorkspaces = LogAnalyticsWorkspaces
except Exception:
    pass
