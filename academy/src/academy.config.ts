// Branding / wiring defaults for this Academy instance.
//
// TEMPLATE NOTE: to repurpose this app for a different academy, replace the
// `src/lessons/` directory with your own lessons and edit the values below.
// Everything else (renderer, quiz engine, store, layout) is framework code you
// should not need to touch.

export interface AcademyConfig {
  /** Title shown in the sidebar / browser. */
  title: string;
  /**
   * Base URL of a full HMM Studio deployment. When set, lessons that ship a
   * topology preset show an "Open in HMM Studio" link pointing at
   * `${studioUrl}/topology`. Empty string => link hidden (pure static mode).
   */
  studioUrl: string;
}

export const DEFAULT_CONFIG: AcademyConfig = {
  title: "HMM Academy",
  studioUrl: "",
};
