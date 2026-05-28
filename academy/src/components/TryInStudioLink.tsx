import { getStudioUrl } from "../runtimeConfig";

interface TryInStudioLinkProps {
  /** The lesson's topology preset YAML (presence drives whether to show). */
  yaml?: string;
}

/**
 * Standalone replacement for the studio's in-app "Try in editor" bridge.
 * Renders an external link to a configured HMM Studio deployment, or nothing
 * when no studio URL is configured (pure static learning mode).
 */
export function TryInStudioLink({ yaml }: TryInStudioLinkProps) {
  const studioUrl = getStudioUrl();
  if (!yaml || !studioUrl) return null;
  const href = `${studioUrl.replace(/\/+$/, "")}/topology`;
  return (
    <div className="mb-6 flex items-center gap-3">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="px-3 py-1.5 rounded text-sm bg-brand-600 text-white hover:bg-brand-700"
      >
        ↗ Open in HMM Studio
      </a>
      <span className="text-xs text-slate-500">
        Opens the topology editor in the full studio.
      </span>
    </div>
  );
}
