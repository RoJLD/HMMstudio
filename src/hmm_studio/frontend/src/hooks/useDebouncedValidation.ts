import { useEffect, useState } from "react";
import { useTopologyStore } from "../store/topologyStore";
import { topologyToYAML } from "../lib/yaml";
import { validateTopology } from "../api/client";

export interface ValidationResult {
  error: string | null;
  summary: string | null;
}

const EMPTY: ValidationResult = { error: null, summary: null };

export function useDebouncedValidation(delayMs = 400): ValidationResult {
  const states = useTopologyStore((s) => s.states);
  const transitions = useTopologyStore((s) => s.transitions);
  const emission = useTopologyStore((s) => s.emission);
  const name = useTopologyStore((s) => s.name);
  const init = useTopologyStore((s) => s.init);
  const fit = useTopologyStore((s) => s.fit);
  const startprob = useTopologyStore((s) => s.startprob);

  const [result, setResult] = useState<ValidationResult>(EMPTY);

  useEffect(() => {
    if (states.length === 0) {
      setResult({ error: "no states yet — add at least one", summary: null });
      return;
    }
    const handle = setTimeout(async () => {
      const yamlText = topologyToYAML(useTopologyStore.getState());
      try {
        const r = await validateTopology(yamlText);
        if (r.valid) {
          setResult({ error: null, summary: r.summary });
        } else {
          setResult({ error: r.error ?? "invalid", summary: null });
        }
      } catch (e) {
        setResult({
          error: e instanceof Error ? e.message : "network error",
          summary: null,
        });
      }
    }, delayMs);
    return () => clearTimeout(handle);
  }, [states, transitions, emission, name, init, fit, startprob, delayMs]);

  return result;
}
