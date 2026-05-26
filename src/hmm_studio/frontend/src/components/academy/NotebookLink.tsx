/**
 * "Run this lesson in a notebook" launcher card.
 *
 * Surfaces a Jupyter notebook companion at the bottom of an Academy
 * lesson, with 4 entry points : Binder (zero-install cloud), Colab
 * (familiar to ML researchers), GitHub (read-only view + raw download),
 * and direct .ipynb download for local use.
 *
 * Pattern : scikit-learn examples ("Launch binder" / "Download Jupyter
 * notebook" badges on every tutorial). Notebooks stay on GitHub and run
 * via external infrastructure — we just surface the launcher in-app so
 * the user doesn't have to leave the lesson to find them.
 */

export interface NotebookRef {
  /** Filename inside notebooks/, e.g. "05_gmm_nhmm_submodes.ipynb". */
  filename: string;
  /** Short label, e.g. "GMM-NHMM sub-modes — runnable example". */
  title: string;
  /** One-sentence summary of what the notebook does. */
  description: string;
}

const GH_OWNER = "RoJLD";
const GH_REPO = "HMMstudio";
const GH_BRANCH = "main";

interface NotebookLinkProps {
  notebook: NotebookRef;
}

export function NotebookLink({ notebook }: NotebookLinkProps) {
  const { filename, title, description } = notebook;
  const binderUrl = `https://mybinder.org/v2/gh/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}?urlpath=lab/tree/notebooks/${filename}`;
  const colabUrl = `https://colab.research.google.com/github/${GH_OWNER}/${GH_REPO}/blob/${GH_BRANCH}/notebooks/${filename}`;
  const githubUrl = `https://github.com/${GH_OWNER}/${GH_REPO}/blob/${GH_BRANCH}/notebooks/${filename}`;
  const rawUrl = `https://raw.githubusercontent.com/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}/notebooks/${filename}`;

  return (
    <section className="mt-10 rounded-lg border border-indigo-200 bg-indigo-50/60 p-5">
      <div className="flex items-start gap-3 mb-3">
        <span className="text-2xl leading-none" aria-hidden>
          📓
        </span>
        <div className="flex-1">
          <h3 className="font-semibold text-indigo-900">{title}</h3>
          <p className="text-sm text-slate-700 mt-1">{description}</p>
          <p className="text-xs text-slate-500 mt-1 font-mono">
            notebooks/{filename}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <NotebookButton
          href={binderUrl}
          label="Launch in Binder"
          hint="Zero install, ~30s spin-up"
        />
        <NotebookButton
          href={colabUrl}
          label="Open in Colab"
          hint="Google Colab notebook"
        />
        <NotebookButton
          href={githubUrl}
          label="View on GitHub"
          hint="Read rendered notebook"
        />
        <NotebookButton
          href={rawUrl}
          label="Download .ipynb"
          hint="Run locally with Jupyter"
          download={filename}
        />
      </div>
    </section>
  );
}

interface NotebookButtonProps {
  href: string;
  label: string;
  hint: string;
  download?: string;
}

function NotebookButton({ href, label, hint, download }: NotebookButtonProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      download={download}
      className="block rounded border border-indigo-300 bg-white px-3 py-2 text-center hover:bg-indigo-50 hover:border-indigo-400 transition-colors"
      title={hint}
    >
      <span className="block text-xs font-medium text-indigo-700">{label}</span>
      <span className="block text-[10px] text-slate-500 mt-0.5">{hint}</span>
    </a>
  );
}
