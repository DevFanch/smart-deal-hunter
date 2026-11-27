/** Service worker minimal : ouvre le side panel au clic sur l'icône.
 *  Aucun code distant, aucune navigation, aucune donnée collectée. */
chrome.runtime.onInstalled.addListener(() => {
  void chrome.sidePanel?.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => undefined);
});
