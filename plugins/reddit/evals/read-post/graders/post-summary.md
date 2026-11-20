---
type: llm
---
The user asked for a summary of a Reddit post. The facts of the post:

- "Intel 9900K Underclocking/Power Limit Experiments", r/buildapc, by u/willswill, posted 2022-08-07.
- The author tested an i9-9900K (with a -50 mV undervolt offset) at lower short- and long-term
  power limits (PL1/PL2), from the default 210 W / 95 W down to 15 W, changing only those two
  BIOS settings.
- Results table: single-threaded performance stays near 100% down to 35 W (92.9% at 25 W,
  68% at 15 W). Multi-threaded drops steadily (92% at 95 W, 61% at 35 W, 26% at 15 W).
  Forza Horizon 5 stays at 79 fps down to 25 W (74 fps with lower minimums at 15 W).
- At 35 W it still boosted to 4.8-4.9 GHz single-threaded, beating the 9900T. Conclusion: an
  unlocked chip can imitate a low-TDP variant through power limits.

PASS if the summary describes this post correctly: the power-limit / underclocking experiment
on the 9900K and its main finding (single-threaded and gaming performance hold up at much lower
power limits while multi-threaded performance falls). It may leave out numbers.

FAIL if the summary is about a different post, gets the main finding wrong, states numbers that
contradict the facts above, or says it could not read the post.
