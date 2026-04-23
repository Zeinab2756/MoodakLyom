# VALIDATION_REPORT

Validation target: prove whether the acoustic branch is actually detecting tone, rather than simply echoing the text branch.

Validation commands used:

```powershell
python scripts/diagnose_mood.py tests/fixtures/validation/same_text_1_happy.wav
pytest tests/test_tone_isolation.py -q
```

Fixture source:

- `tests/fixtures/validation/` uses 18 short human-speech clips derived from RAVDESS.
- All clips were trimmed and resampled to `16 kHz` mono WAV.
- Because RAVDESS speech content is lexically neutral, the "inverted sentiment" scenarios below are disagreement proxies, not literal positive-text/negative-tone sentences.

## Section 1: Same-Text Tone Separation

Three triplets were built from the same spoken sentence in different tones. The acoustic branch was run directly, while the text branch was allowed to transcribe and classify the resulting text.

| Fixture | Intended tone | Acoustic top | Text top | Match with intended tone? |
| --- | --- | --- | --- | --- |
| `same_text_1_happy.wav` | happy | `happy (0.875)` | `neutral (1.00)` | PASS |
| `same_text_1_sad.wav` | sad | `sad (0.811)` | `neutral (1.00)` | PASS |
| `same_text_1_angry.wav` | angry | `angry (0.974)` | `neutral (1.00)` | PASS |
| `same_text_2_happy.wav` | happy | `happy (0.792)` | `neutral (1.00)` | PASS |
| `same_text_2_sad.wav` | sad | `sad (0.889)` | `neutral (1.00)` | PASS |
| `same_text_2_neutral.wav` | neutral | `neutral (0.969)` | `neutral (1.00)` | PASS |
| `same_text_3_happy.wav` | happy | `happy (0.871)` | `neutral (1.00)` | PASS |
| `same_text_3_sad.wav` | sad | `sad (0.881)` | `neutral (1.00)` | PASS |
| `same_text_3_angry.wav` | angry | `angry (0.979)` | `neutral (1.00)` | PASS |

Pairwise acoustic-distribution separation:

- `same_text_1` average L1 distance: `1.854`
- `same_text_2` average L1 distance: `1.906`
- `same_text_3` average L1 distance: `1.897`

Interpretation:

- The acoustic branch is clearly not collapsing to a single neutral output. The same words in different tones produced strongly different distributions, with pairwise L1 distances around `1.85-1.91` on a scale whose maximum is `2.0`.
- On this acted-speech validation set, the acoustic top label matched the intended tone for `9/9` same-text fixtures.
- The text branch did not provide meaningful separation here. It returned `neutral` on all nine clips.

## Section 2: Sarcasm / Inversion Handling

These are proxy disagreement cases. Because the source corpus is lexically neutral, they validate whether text and tone can diverge, not whether the system fully understands literal positive-vs-negative sentiment inversion.

| Fixture | Transcript | Text top | Acoustic top | `sarcasm_suspected` | Outcome |
| --- | --- | --- | --- | --- | --- |
| `inverted_01.wav` | `Kids are talking by the door.` | `neutral (1.00)` | `sad (0.881)` | `true` | disagreement detected |
| `inverted_02.wav` | `Dogs are sitting by the door!` | `neutral (1.00)` | `happy (0.792)` | `true` | disagreement detected |
| `inverted_03.wav` | `kids are talking by the door.` | `neutral (1.00)` | `happy (0.321)` | `false` | disagreement exists, but below sarcasm threshold |

Interpretation:

- The disagreement mechanism is real. In `3/3` proxy inversion cases, the acoustic top label differed from the text top label.
- The sarcasm flag fired in `2/3` cases. The third case did not fire because the acoustic confidence was only `0.321`, below the current `>0.6` threshold.
- This means the flag is not decorative, but it is currently more a "high-confidence branch disagreement" detector than a true sarcasm detector.

## Section 3: Intensity Resolution

RAVDESS only provides neutral plus two emotional intensities, so the "mild" rung below is a neutral-tone proxy rather than a literal weakly emotional version of the same sentence.

### Happy ladder

Target `happy` confidence:

```text
mild       0.013  |█
moderate   0.706  |██████████████
exuberant  0.875  |██████████████████
```

Observed labels:

- `intensity_happy_mild.wav` -> `neutral (0.968)`
- `intensity_happy_moderate.wav` -> `happy (0.706)`
- `intensity_happy_exuberant.wav` -> `happy (0.875)`

### Angry ladder

Target `angry` confidence:

```text
mild         0.003  |█
frustrated   0.919  |██████████████████
shouting     0.974  |███████████████████
```

Observed labels:

- `intensity_angry_mild.wav` -> `neutral (0.968)`
- `intensity_angry_frustrated.wav` -> `angry (0.919)`
- `intensity_angry_shouting.wav` -> `angry (0.974)`

Interpretation:

- Both proxy ladders were monotonic.
- The angry ladder is especially strong; the model sharply separates neutral from angry and increases confidence further on the stronger clip.
- The happy ladder also increases cleanly, though it depends on actor choice more than sad/angry do.

## Section 4: The Verdict

WARNING: Tone detection is partially working.

Why this is the honest verdict:

- The acoustic branch itself is real and strong on clean acted speech. It separated same-text emotional variants with average pairwise L1 distances near `1.9`, and matched intended tone on `9/9` same-text fixtures.
- The intensity probes were also monotonic for both happy and angry.
- But the multimodal story is weaker than the API suggests because the text branch did **not** run the intended BERT path during validation. On all `18/18` validation fixtures, `predict_text_emotion()` fell back to the `keyword` backend and returned `neutral`.
- As a result, the current `sarcasm_suspected` behavior is mostly "tone disagrees with neutral text fallback" rather than a robust lexical-vs-prosodic contradiction detector.

If the question is "does the acoustic branch hear tone?" the answer is yes on this validation set.

If the question is "is the full multimodal sarcasm feature production-trustworthy?" the answer is not yet.

## Section 5: Known Limitations

- The text branch fell back to `keyword` on `18/18` validation clips. The intended local BERT-primary path is not what handled these fixtures during validation.
- RAVDESS is acted English speech. The results here are a useful proof of signal, not a guarantee of performance on spontaneous conversational audio.
- The validation corpus is lexically neutral. That means the inversion section validates disagreement mechanics, not literal positive-words/negative-tone sarcasm.
- The sarcasm flag requires both branches to exceed `0.6` confidence. Lower-confidence disagreements, such as `inverted_03.wav`, do not raise the flag even when the branches differ.
- ASR quality on emotional speech is imperfect. Some clips transcribed as variants like `Don't hesitate by the door.` or `Can't they're talking by the door?`, though this did not materially change the text branch outcome because it was already falling back to keyword-neutral behavior.
- The happy intensity ladder uses a neutral clip as the low-intensity proxy because the source corpus does not provide a true three-step happy ladder.
- The browser recorder depends on a running local backend and inherits the backend's current model behavior, including the weak text branch.
