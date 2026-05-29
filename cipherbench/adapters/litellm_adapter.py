"""CipherBench LiteLLM adapter — provider-agnostic completion interface.

This module contains one public name:
  LiteLLMAdapter  — thin wrapper around litellm.completion() with retry and
                    token-budget checking.

Design decisions implemented here:
  ADAPT-01  single complete(messages) interface — all callers use this;
            no caller ever touches litellm.ModelResponse directly.
  ADAPT-02  token budget check via litellm.token_counter + litellm.get_max_tokens;
            None-safe guard logs a warning and returns when model is unknown.
  ADAPT-03  tenacity retry on litellm.RateLimitError with random exponential
            backoff; reraise=True propagates the error after MAX_RETRIES exhaustion.

Information security (threat model T-03-02-01):
  API keys are read from provider env vars by LiteLLM automatically.
  They are never accepted as constructor arguments, stored as attributes,
  or logged at any severity level.

Private attribute convention (mirrors rule_engine.py D-09):
  Single-underscore convention (_model, _extra_kwargs) is used rather than
  double-underscore name-mangling by deliberate choice.
"""
from __future__ import annotations

import logging

import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

MAX_RETRIES: int = 5
TOKEN_BUDGET_THRESHOLD: float = 0.80  # warn if projected use > 80% of context window (D-16)


class LiteLLMAdapter:
    """Provider-agnostic LLM completion adapter wrapping litellm.completion().

    Owns retry logic (ADAPT-03), token budget checking (ADAPT-02), and the
    single complete() interface (ADAPT-01).  Callers never interact with
    litellm directly.

    Private attributes (single-underscore convention, D-09):
      _model             : str        — LiteLLM model string (e.g. 'openai/gpt-4o')
      _litellm_config_path : str | None — path to LiteLLM config.yaml (escape hatch, D-14)
      _extra_kwargs      : dict       — additional kwargs forwarded to litellm.completion()

    Never instantiate this class without a non-empty model string.
    """

    def __init__(self, model: str, litellm_config_path: str | None = None) -> None:
        """Initialise the adapter with a LiteLLM model string.

        Parameters
        ----------
        model : str
            LiteLLM model string, e.g. 'anthropic/claude-opus-4-7', 'openai/gpt-4o'.
            Must be a non-empty string.
        litellm_config_path : str | None, optional
            Path to a LiteLLM config.yaml for advanced proxy routing (D-14 escape hatch).
            Stored but not deeply integrated in v1; passed as api_base kwarg when provided.

        Raises
        ------
        ValueError
            If ``model`` is not a non-empty string.
        """
        if not model or not isinstance(model, str):
            raise ValueError("model must be a non-empty string")

        self._model: str = model
        self._litellm_config_path: str | None = litellm_config_path
        self._extra_kwargs: dict = {}

        # D-14 escape hatch: low-priority in v1 — store path, forward as api_base if set.
        # This is the minimal integration per the open question in RESEARCH.md.
        if litellm_config_path is not None:
            self._extra_kwargs["api_base"] = litellm_config_path

    @retry(
        retry=retry_if_exception_type(litellm.RateLimitError),
        wait=wait_random_exponential(multiplier=1, max=60),
        stop=stop_after_attempt(MAX_RETRIES),
        reraise=True,  # re-raise after exhaustion so session runner detects rate_limited
    )
    def complete(self, messages: list[dict]) -> str:
        """Call litellm.completion() and return the response content string.

        Decorated with tenacity retry on litellm.RateLimitError (ADAPT-03).
        After MAX_RETRIES exhaustion, reraise=True propagates the error to the caller.

        Only RateLimitError is handled here.  AuthenticationError, BadRequestError,
        and all other exceptions propagate immediately (no catch in this method).

        Parameters
        ----------
        messages : list[dict]
            OpenAI-format messages list, e.g. [{"role": "user", "content": "..."}].
            Must be a non-empty list.

        Returns
        -------
        str
            The response content string from the model.

        Raises
        ------
        ValueError
            If ``messages`` is empty or not a list.
        litellm.RateLimitError
            Re-raised by tenacity after MAX_RETRIES exhaustion (ADAPT-03, D-16).
        """
        # Input validation (T-03-02-02 mitigation)
        if not messages or not isinstance(messages, list):
            raise ValueError("messages must be a non-empty list")

        response = litellm.completion(
            model=self._model,
            messages=messages,
            **self._extra_kwargs,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""  # CR-03: guard None for empty/tool-use responses

    def check_token_budget(self, messages: list[dict]) -> None:
        """Check projected token usage against the model's context window.

        Calls litellm.token_counter() and litellm.get_max_tokens() and logs a
        warning if projected usage exceeds TOKEN_BUDGET_THRESHOLD of the context
        window.  Advisory only — never raises; never aborts the session.

        None-safe guard (Pitfall 4 / ADAPT-02): if get_max_tokens() returns None
        for an unknown model, logs a warning and returns immediately without
        attempting a comparison (which would raise TypeError).

        Parameters
        ----------
        messages : list[dict]
            OpenAI-format messages list to count tokens for.

        Returns
        -------
        None
        """
        used = litellm.token_counter(model=self._model, messages=messages)
        max_tokens = litellm.get_max_tokens(self._model)

        # None-safe guard — unknown models not in LiteLLM model database (Pitfall 4)
        if max_tokens is None:
            logger.warning(
                "Cannot check token budget: model %s not in LiteLLM model database",
                self._model,
            )
            return

        if used > TOKEN_BUDGET_THRESHOLD * max_tokens:
            logger.warning(
                "Token budget warning: projected %d tokens exceeds %d%% of %d context "
                "window for model %s",
                used,
                int(TOKEN_BUDGET_THRESHOLD * 100),
                max_tokens,
                self._model,
            )
