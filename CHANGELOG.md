# Changelog

## 0.1.3

- Improved team search without hiding similar participants.
- Added clearer dropdown labels with participant ID, tournament and category when upcoming fixture metadata is available.
- Added provider-derived labels for Women, U23/U21/U20/U19/U18/U17/U16 and reserve teams when that information is present in the participant or tournament text.
- Added normalized team search so punctuation and Scandinavian characters such as `Bodø/Glimt` / `Bodo Glimt` are easier to match.
- Added README guidance for finding the correct OddsPapi participant ID.
- Documented Manchester United (`35`), Norway (`4475`) and Bodø/Glimt (`656`) as tested examples.
- Clarified that bookmaker support has currently only been tested and verified with Pinnacle.
- Team-search enrichment uses one shared fixture lookup per setup/options session rather than one API request per result.

## 0.1.2

- Clean HACS-compliant repository structure.
- Added UI config flow with API key validation.
- Added team search and selection.
- Added bookmaker and refresh-profile settings.
- Added quota-aware fixture and odds polling.
- Added Home/Draw/Away, team odds and fair win probability sensors.
- Added English and Norwegian translations.
- Added one-click Open in HACS and Add Integration buttons.
