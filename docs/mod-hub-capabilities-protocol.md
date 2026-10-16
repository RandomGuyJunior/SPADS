# Mod Hub capability protocol (proposed TEI extension)

## Intent

Do not use SAYBATTLE, SAYBATTLEEX, private chat, periodic timers, or user-visible messages to negotiate Mod Hub support. Official BAR servers and clients must remain unaffected.

## Lifecycle

1. A SPADS battle host registers a `rapid-mods-v1` capability against its current battle via an authenticated TEI protocol command when the battle opens. Registration is idempotent and cannot be performed by an arbitrary participant.
2. TEI stores the capability on that battle; it is not persisted beyond battle closure or host disconnection.
3. When a Modded Chobby user joins, TEI emits the current capability state as a non-chat protocol event to **that user only**, after the user's membership in that battle is established. No per-user message is required from SPADS.
4. Chobby applies capabilities only for the battle it is currently in; clears them on leave, switch, disconnect, and battle close; and refreshes Advanced Options tabs if the UI is already open.
5. Clients or servers without support ignore this extension. The tab must remain absent on official SPADS battles.

## Example conceptual wire exchange

These names are illustrative, **not implemented TEI commands**. Final syntax and authorization must follow TEI's existing protocol implementation.

- Host to TEI: `REGISTER_BATTLE_CAPABILITIES rapid-mods-v1`
- TEI to joined client: `BATTLE_CAPABILITIES <battle-id> rapid-mods-v1`

## Security and correctness

- TEI derives battle identity from the authenticated host rather than trusting a supplied battle ID.
- TEI validates recipient membership and delivers only the capabilities for the recipient's current battle.
- Capability advertisement is not an authorization to install a mod: SPADS continues to validate `!mod` permissions and voting.
- The transport is non-chat. No messages should appear in the battle console.

## Integration status

- SPADS RapidMods has removed visible capability broadcasts until the transport is implemented.
- TEI's actual source repository is not currently available through the connected GitHub installation, so event registration, storage, and delivery are **not yet implemented**.
- Modded Chobby's existing battle-chat listener must be replaced with the final TEI event; independently verify that `gui_modoptions_panel.lua` is actually shipped by Rapid and that the tab can update while Advanced Options is open.
