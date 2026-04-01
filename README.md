# Pokemon Border Grader (MVP)

This is a first-pass grader for Pokemon card centering.

Current scope:
- Detects the card in an uploaded image.
- Estimates border thickness on all four sides.
- Reports left/right and top/bottom border ratios.
- Flags pass/fail for a `45/55` centering window.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then upload a card image in the browser UI.

## Notes

- This is a heuristic model, not an official TAG-grade implementation.
- Image quality, glare, and angled photos can affect results.
- Best results come from flat, well-lit scans/photos with clear card edges.
