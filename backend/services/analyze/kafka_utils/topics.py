class Topics:
    # Configuration service
    TOKENS_REQUEST  = "config.tokens.request"   # demande de token
    TOKENS_RESPONSE = "config.tokens.response"  # réponse avec token

    # Collection service
    COLLECTION_STARTED   = "collection.events.started"
    COLLECTION_COMPLETED = "collection.events.completed"
    COLLECTION_FAILED    = "collection.events.failed"

    # Analysis service (legacy)
    ANALYSIS_REQUESTED  = "analysis.events.requested"
    ANALYSIS_COMPLETED  = "analysis.events.completed"

    # Notification service
    NOTIFICATION_EVENTS = "notification.events"

    # --- DSL-First custom analysis ---
    # Published by Analysis Service after a custom DSL analysis completes
    ANALYSIS_DSL_SUBMITTED = "analysis.dsl.submitted"
    ANALYSIS_DSL_EXECUTED  = "analysis.dsl.executed"
    ANALYSIS_DSL_FAILED    = "analysis.dsl.failed"

    # --- Metric Registry (Collection Service) ---
    METRIC_REGISTRY_CREATED = "metric.registry.created"
    METRIC_REGISTRY_UPDATED = "metric.registry.updated"
    METRIC_REGISTRY_DELETED = "metric.registry.deleted"

    # --- Plugin lifecycle (Collection + Analysis Services) ---
    PLUGIN_SUBMITTED  = "plugin.submitted"
    PLUGIN_VALIDATED  = "plugin.validated"
    PLUGIN_FAILED     = "plugin.failed"
    PLUGIN_REGISTERED = "plugin.registered"
