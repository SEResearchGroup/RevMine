const AUTOMATIC_WORKFLOW_STORAGE_PREFIX = "automatic_collection_workflow_";

export const getAutomaticWorkflowStorageKey = (planId) =>
  `${AUTOMATIC_WORKFLOW_STORAGE_PREFIX}${planId}`;

export const persistAutomaticWorkflow = (planId, workflow) => {
  if (typeof window === "undefined" || !planId || !workflow) {
    return;
  }

  window.localStorage.setItem(
    getAutomaticWorkflowStorageKey(planId),
    JSON.stringify(workflow)
  );
};

export const readAutomaticWorkflow = (planId) => {
  if (typeof window === "undefined" || !planId) {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(
      getAutomaticWorkflowStorageKey(planId)
    );
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
};

export const clearAutomaticWorkflow = (planId) => {
  if (typeof window === "undefined" || !planId) {
    return;
  }

  window.localStorage.removeItem(getAutomaticWorkflowStorageKey(planId));
};

export const sanitizeAutomaticCleaningDraft = (draft, cleaningConfig) => {
  const availableAuthors = new Set(
    cleaningConfig?.available_filters?.authors || []
  );
  const availableExtensions = new Set(
    cleaningConfig?.available_filters?.file_extensions || []
  );
  const runtimeWarnings = [];

  const sanitizedAuthors = (draft?.filters?.authors || []).filter((author) => {
    if (availableAuthors.size === 0 || availableAuthors.has(author)) {
      return true;
    }

    runtimeWarnings.push(
      `Author '${author}' was removed because it is not present in the collected dataset.`
    );
    return false;
  });

  const sanitizedExtensions = (draft?.filters?.file_extensions || []).filter(
    (extension) => {
      if (availableExtensions.size === 0 || availableExtensions.has(extension)) {
        return true;
      }

      runtimeWarnings.push(
        `File extension '${extension}' was removed because it is not present in the collected dataset.`
      );
      return false;
    }
  );

  return {
    payload: {
      collection_id: null,
      start_date: draft?.start_date || null,
      end_date: draft?.end_date || null,
      filters: {
        authors: sanitizedAuthors,
        file_extensions: sanitizedExtensions,
        keyword_filters: draft?.filters?.keyword_filters || [],
      },
      selected_features: draft?.selected_features || [],
    },
    runtimeWarnings,
  };
};
