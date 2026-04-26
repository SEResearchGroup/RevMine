export const LLM_PROVIDERS = {
  OPENROUTER: "openrouter",
  OLLAMA: "ollama",
};

export const OPENROUTER_MODELS = [
  { id: "openai/gpt-4o-mini", name: "GPT-4o Mini (OpenAI)" },
  { id: "meta-llama/llama-3.1-8b-instruct", name: "Llama 3.1 8B (Free)" },
  { id: "google/gemma-3-4b-it", name: "Gemma 3 4B (Free)" },
  { id: "microsoft/phi-3-mini-128k-instruct", name: "Phi-3 Mini (Free)" },
  { id: "qwen/qwen3-8b", name: "Qwen3 8B (Free)" },
  { id: "deepseek/deepseek-r1", name: "DeepSeek R1 (Free)" },
];

export const DEFAULT_OPENROUTER_MODEL = OPENROUTER_MODELS[0].id;
export const DEFAULT_OLLAMA_MODEL = "deepseek-r1";

export const defaultModelForProvider = (provider) =>
  provider === LLM_PROVIDERS.OLLAMA ? DEFAULT_OLLAMA_MODEL : DEFAULT_OPENROUTER_MODEL;
