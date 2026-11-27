# context-band

## Crab work: always render the crabs

When a change can affect how the crab looks, render the crabs and show them to the user before calling the work done. Tests passing is not enough. This covers anything that could change the crab:

- `hooks/crab.ts`: shapes, colours, CSS, keyframes, timings, extras, class names
- moods and the pace: `moodOf`, `hasPace`, `canCool`, the pace levels and thresholds in `hooks/pace.ts`
- when a mood shows: `hooks/activity.ts`, `hooks/awake.ts`, the `AbovePrompt` hook in `hooks/register.tsx`

Render every mood or level the change touches, each pace level from calm to meltdown where the pace shows, and the asleep crab for contrast.

How:

1. A small script imports `crabSvg` and `crabAlt` from `hooks/crab.ts` and writes an HTML page. Run it with `npx -y tsx <script>`.
2. Put each SVG in an `<img>` as a `data:image/svg+xml;base64,...` URI. Every SVG carries its own `<style>`, so inline SVGs on one page would share and clash with each other's rules.
3. Serve the page from localhost: add a `python3 -m http.server` entry to `.claude/launch.json` (git-excluded), pointed at a scratchpad folder, and open it with `preview_start`. A `file://` page shows in the app's browser pane as a static snapshot, with no animation.
4. Take a screenshot to check it renders, and leave the page open for the user to watch it animate.
