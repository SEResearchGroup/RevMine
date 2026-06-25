class Topics:
    # Configuration service
    TOKENS_REQUEST  = "config.tokens.request"   # get tokens request
    TOKENS_RESPONSE = "config.tokens.response"  # response with token

    # Collection service
    COLLECTION_STARTED   = "collection.events.started"
    COLLECTION_COMPLETED = "collection.events.completed"
    COLLECTION_FAILED    = "collection.events.failed"

    # Analysis service (legacy)
    ANALYSIS_REQUESTED  = "analysis.events.requested"
    ANALYSIS_COMPLETED  = "analysis.events.completed"

    # Notification service
    NOTIFICATION_EVENTS = "notification.events"

    # --- Metric Registry ---
    # Published when a MetricPlugin is added/updated/removed from the registry
    METRIC_REGISTRY_CREATED = "metric.registry.created"
    METRIC_REGISTRY_UPDATED = "metric.registry.updated"
    METRIC_REGISTRY_DELETED = "metric.registry.deleted"

    # --- Plugin lifecycle ---
    PLUGIN_SUBMITTED  = "plugin.submitted"
    PLUGIN_VALIDATED  = "plugin.validated"
    PLUGIN_FAILED     = "plugin.failed"
    PLUGIN_REGISTERED = "plugin.registered"
