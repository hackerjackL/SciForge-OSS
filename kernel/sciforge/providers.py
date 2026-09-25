"""Provider abstraction (S03/S23): role-tiered multi-backend LLM routing with real usage accounting.

Lessons taken:
- STORM: per-role model config (cheap model for grunt work, strong model for judgment).
- AI-Scientist v2: retry/backoff + real token tracking feeding the cost ledger.
- ScienceDiscovery: sidecar never holds keys — calls go through the control plane;
  here the kernel is the control plane, keys live in env/config only.

Backends: anthropic (Messages API), openai-compatible (incl. Ollama/vLLM via base_url).
No third-party deps: urllib over https. Roles map to models in kernel/config/providers.json.

Usage is measured per call: input_tokens, output_tokens, cached tokens when the backend
reports them — RUN_BUDGET.api_cost_usd becomes a real number, not an agent self-report.
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "providers.json")

# Role tiers: which role does which kind of work (phase roles from auto-pipeline).
ROLES = ("ideation", "retrieval", "reasoning", "coding", "grading", "review",
         "adjudication", "writing")


class ProviderError(RuntimeError):
    pass


def load_config(path: str | None = None) -> dict:
    p = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return json.load(f)


class CallRecord:
    __slots__ = ("role", "backend", "model", "input_tokens", "output_tokens",
                 "cached_tokens", "latency_s", "cost_usd", "ok", "retries", "ts")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


class Providers:
    """Routes a role -> backend/model, executes chat completion, returns (text, usage)."""

    def __init__(self, config: dict | None = None, config_path: str | None = None):
        self.cfg = config if config is not None else load_config(config_path)
        self.backends = self.cfg.get("backends", {})
        self.roles = self.cfg.get("roles", {})
        self.pricing = self.cfg.get("pricing_usd_per_mtok", {})
        self.usage_log: list[dict] = []
        self.total_cost = 0.0
        # host mode: no providers configured -> the host agent (claude/codex) does
        # the LLM work; the kernel only tracks cost if the host reports it.
        self.host_mode = not self.backends

    def model_for(self, role: str) -> dict:
        entry = self.roles.get(role) or self.roles.get("default") or {}
        if not entry:
            if self.host_mode:
                raise ProviderError("host_mode: no provider configured (kernel delegates LLM work to host agent)")
            raise ProviderError(f"role '{role}' unmapped in kernel/config/providers.json")
        return entry

    def _cost(self, backend: str, model: str, rec: CallRecord) -> float:
        price = self.pricing.get(f"{model}") or self.pricing.get(backend, {})
        if isinstance(price, (int, float)):  # flat $/Mtok symmetric
            return (rec.input_tokens + rec.output_tokens) / 1e6 * price
        i = price.get("input", 0.0); o = price.get("output", 0.0); c = price.get("cache_read", i * 0.1)
        return (rec.input_tokens * i + rec.output_tokens * o + rec.cached_tokens * c) / 1e6

    def complete(self, role: str, system: str, prompt: str, *,
                 max_tokens: int = 4096, temperature: float = 0.3,
                 retries: int = 2, backoff: float = 1.0,
                 json_schema: dict | None = None) -> tuple[str, CallRecord]:
        """Single completion with retries+backoff. Retries count toward CallRecord.retries."""
        if self.host_mode:
            raise ProviderError("host_mode active: LLM work belongs to the host agent, not providers.complete()")
        entry = self.model_for(role)
        backend_name = entry["backend"]; model = entry["model"]
        backend = self.backends[backend_name]
        base = backend["base_url"].rstrip("/")
        key_env = backend.get("api_key_env", "")
        key = os.environ.get(key_env, "") if key_env else ""
        if backend_name == "anthropic" and not key and not os.environ.get("ANTHROPIC_API_KEY"):
            # Claude Code login sets proxy-managed keys; direct API needs ANTHROPIC_API_KEY.
            raise ProviderError(f"backend {backend_name}: set {key_env or 'ANTHROPIC_API_KEY'}")
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                text, usage = self._raw_call(backend_name, base, key, model, system, prompt,
                                              max_tokens, temperature, json_schema)
                rec = CallRecord(role=role, backend=backend_name, model=model,
                                 input_tokens=usage.get("input_tokens", 0),
                                 output_tokens=usage.get("output_tokens", 0),
                                 cached_tokens=usage.get("cached_tokens", 0),
                                 latency_s=0.0, ok=True, retries=attempt, ts=time.time())
                rec.cost_usd = self._cost(backend_name, model, rec)
                self.total_cost += rec.cost_usd
                rec.latency_s = usage.pop("_latency", 0.0)
                self.usage_log.append(rec.as_dict())
                return text, rec
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(backoff * (2 ** attempt) + random.uniform(0, 0.5))
                    continue
        rec = CallRecord(role=role, backend=backend_name, model=model, input_tokens=0,
                         output_tokens=0, cached_tokens=0, latency_s=0.0, cost_usd=0.0,
                         ok=False, retries=retries, ts=time.time())
        self.usage_log.append(rec.as_dict())
        raise ProviderError(f"role={role} backend={backend_name} failed after {retries} retries: {last_err}")

    def _raw_call(self, name, base, key, model, system, prompt, max_tokens, temperature, json_schema):
        t0 = time.time()
        if name == "anthropic":
            body = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
                    "system": system, "messages": [{"role": "user", "content": prompt}]}
            if json_schema:
                body["tools"] = [{"name": "structured_output", "description": "Return the final answer as validated JSON.",
                                  "input_schema": json_schema}]
                body["tool_choice"] = {"type": "tool", "name": "structured_output"}
            headers = {"content-type": "application/json",
                       "x-api-key": key or os.environ.get("ANTHROPIC_API_KEY", ""),
                       "anthropic-version": "2023-06-01"}
            req = urllib.request.Request(f"{base}/v1/messages", data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read())
            text = "".join(b.get("text", "") if b["type"] == "text" else
                           json.dumps(b.get("input", {})) for b in data["content"])
            u = data.get("usage", {})
            usage = {"input_tokens": u.get("input_tokens", 0),
                     "output_tokens": u.get("output_tokens", 0),
                     "cached_tokens": u.get("cache_read_input_tokens", 0)}
        else:  # openai-compatible (openai, ollama, vllm, any base_url)
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            body = {"model": model, "messages": msgs, "max_tokens": max_tokens,
                    "temperature": temperature}
            if json_schema:
                body["response_format"] = {"type": "json_object"}
            headers = {"content-type": "application/json"}
            if key:
                headers["authorization"] = f"Bearer {key}"
            req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read())
            text = data["choices"][0]["message"]["content"]
            u = data.get("usage", {})
            usage = {"input_tokens": u.get("prompt_tokens", 0),
                     "output_tokens": u.get("completion_tokens", 0),
                     "cached_tokens": u.get("prompt_tokens_details", {}).get("cached_tokens", 0)}
        usage["_latency"] = round(time.time() - t0, 3)
        return text, usage
