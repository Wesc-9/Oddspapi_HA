# Changelog

## 1.0.1

- Improved team selection when OddsPapi returns several participants with the same normalized name.
- Duplicate-name search results are now enriched before the user selects a team.
- The dropdown can show tournament, country/category and provider-derived team type such as Women, U23/U21/U20/U19/U18/U17/U16, Youth, Reserves or SRL when OddsPapi fixture metadata exposes it.
- The selected bookmaker is checked first, so matching results can show that upcoming odds are available for that bookmaker.
- If the selected bookmaker has no upcoming odds for a duplicate participant, the integration performs a fallback fixture lookup to identify the competition/team type where possible.
- No participant is hidden or filtered out; the extra information is only used to make the correct participant easier to identify.
- Search enrichment is cached for the active config/options flow and is capped at 8 fixture requests per flow to protect small OddsPapi quotas.
- Removed the previous always-on shared fixture lookup from team search; unique-name searches now avoid unnecessary fixture enrichment requests.

## 1.0.0

- First stable release of OddsPapi Sports Odds for Home Assistant.
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
