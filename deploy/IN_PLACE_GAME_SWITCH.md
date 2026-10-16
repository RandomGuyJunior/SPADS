# In-place battle game switching (Modded BAR)

Status: **protocol design; TEI server support is not yet deployed**. SPADS
MUST NOT call `rehost()` or change `hSet.modName` expecting the current battle
game to update: stock SPADS advertises a game's name/hash during OPENBATTLE.

## Preconditions

- A custom TEI-hosted battle registered `rapid-mods-v1`.
- No match is running or starting.
- Request authenticated as the *founder of the existing battle*, not as an
  ordinary player. TEI must verify this against live battle ownership.
- Selected wrapper exists on SPADS, unitsync has indexed it, and its game hash
  and identity are known.
- A fresh monotonically increasing revision is assigned to each game change.

## Proposed host command (not supported on TEI yet)

`c.battle.change_game <battleId> <revision> <gameHash> <base64url-json>`

JSON keys: `game_name`, `game_hash`, `revision`, `foundation_tag`,
`mods` (ordered array of `{tag, package_hash, archive_name}`),
`fingerprint`. TEI should impose packet length and field limits, validate
types and reject any untrusted/unauthorized requester.

The authoritative game identity and game hash must be consistent with the
server's unitsync archive identity. The `fingerprint` is derived from
*pinned* archive hashes, not mutable Rapid tag strings.

TEI success response:
`s.battle.game_changed <battleId> <revision> <gameHash> <base64url-json>`
TEI error response:
`s.battle.game_change_failed <battleId> <revision> <reason>`

TEI must atomically update the stored battle game and hash and broadcast the
new game identity to **existing battle occupants and battle-list subscribers**.
The current battle ID, founder, participants, colors, teams, chat and map
must remain intact. The new game is replayed to late joiners. Readiness must
be invalidated for participants until Chobby verifies local content.

The TEI implementation must be reviewed against the actual server protocol
state machine before any command is emitted by SPADS. A chat status message
or `s.battle.extra_data` alone is *not* sufficient to change the authoritative
game selected by lobby clients.

## SPADS integration sequence

1. Gather **enabled mods**, not all historically downloaded mods.
2. Download any missing tags as a batch.
3. Resolve exact installed package hashes and archive names.
4. Write a new, uniquely fingerprinted wrapper; never mutate the currently
   active wrapper in place while it may be used by a match.
5. Refresh unitsync **once** only if new archives were installed or wrapper
   content changed.
6. Validate unitsync game name, checksum, and mod options before proposing
   switch. Keep old battle game on failure.
7. Request in-place change. Wait for TEI acknowledgment with matching revision
   and game hash. Never call `rehost()`.
8. Advertise pinned mod manifest to every Chobby client, and require matching
   client fingerprints/ready acknowledgments before START.
9. Set the SPADS engine launch game only after the acknowledged switch.
10. On timeout, mismatched fingerprint or TEI error, keep old battle game.

TEI's actual implementation is a prerequisite. Do not call this feature
ready for a live Underwater AFUS multiplayer test without it.
