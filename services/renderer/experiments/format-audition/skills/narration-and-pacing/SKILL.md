---
name: narration-and-pacing
description: Align these Remotion auditions to cached provider speech and word timestamps.
---

# Narration And Pacing

The user finds the repeated narrator annoying and now explicitly prioritizes male voices. Default to a clear male lead, vary the lead between videos, and use a second male voice only when a brief reaction adds something. Cast distinct available voices per role and vary the lead voice between future videos. Record role, voice ID, model and delivery in each manifest; do not merely change pitch on the same recording and call it a new actor. Use contrasting timbre, energy and accent where useful. Keep a character's voice consistent within its story. See ../../../friction-story/storyboard.json and ../../../friction-story/prepare.py for a three-voice example. Stock voice descriptions are casting hints; user listening feedback determines whether the pairing works. This is an authoring rule, not an implemented production feed voice scheduler.

Reuse prepare.py and the existing ElevenLabs adapter. Keep credentials outside the render pack; synthesis runs server-side. Match raw character alignment exactly to frozen text, then offset by frame-rounded segment starts. Cache by text, voice, model and settings. Changing words requires fresh alignment. Preserve actual prediction silence. No automatic speed-up to hide an overlong script. Review a full audio/video segment; frame checks alone do not establish natural delivery or sync.

These instructions are local candidate skills for the format audition. User review determines which formats to retain; they are not globally installed.
