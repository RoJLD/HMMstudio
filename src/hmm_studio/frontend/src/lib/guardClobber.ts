/** Decide whether to proceed with an action that REPLACES the current model.
 *  Pure + injectable prompts for testability.
 *  - currentStateCount === 0 → proceed silently (nothing to lose).
 *  - else ask "save current first?": if yes → onSave() then proceed; if the
 *    user dismisses the save dialog, still ask a final confirm to proceed.
 *  Returns true to proceed with the clobber, false to abort.
 *  `wantSave`/`confirmProceed` default to window.confirm in the app. */
export function confirmClobber(
  currentStateCount: number,
  onSave: () => void,
  wantSave: () => boolean = () => window.confirm("Save the current model before replacing it?"),
  confirmProceed: () => boolean = () => window.confirm("Replace the current model without saving?"),
): boolean {
  if (currentStateCount === 0) return true;
  if (wantSave()) {
    onSave();
    return true;
  }
  return confirmProceed();
}
