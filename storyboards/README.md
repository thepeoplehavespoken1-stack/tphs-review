# TPHS storyboards

Each story folder has one picture per scene, in order.

| Folder | Story | Scenes |
|---|---|---|
| `docusign/` | This Is DocuSign | 124 |
| `salesforce/` | This Is Salesforce | 108 |
| `infinity/` | This Is Infinity | 117 |
| `first-acceptance-timeline/` | This Is First Acceptance: The Timeline | 127 |

## Inside each folder
- `frames/NNN_<sceneid>.jpg`: one picture per scene, numbered in play order, tall 9:16.
- `scenes.json`: the script data for every scene, in the same order. Fields:
  - `narration`: the voice-over line, read with the narrator off camera.
  - `avatar`: the line the narrator says on camera.
  - `onscreen`: the words shown on screen.
  - `bottom`: the full picture/shot description.
  - `length`, `motion`, `transition`, `sound`, `music`, `delivery`: timing and editing notes.
  - `citation`: the source for that scene's facts.
  - `yts`, `tt`, `ig`, `fb`, `x`, `th`: true when the scene goes in that platform's short cut.

## Notes for the video build
- Frames are storyboard references. Narrator frames are a stand-in for the narrator avatar clip.
- Some frames for real documents and real photos are 3D stand-ins. Use the real source named in `citation` / `bottom` in the final video.
- Some frames are 720×1280 and others 405×720. Scale every frame to fit 9:16.
- The shot planners are the source of truth. If one changes, re-export.
