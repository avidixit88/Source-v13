# CAS Sourcing MVP v13

Streamlit MVP for CAS-based supplier discovery, supplier-specific public-price parsing, catalog-ladder reasoning, and procurement-ready desired-quantity estimation.

## What v13 adds

- Builds directly on v12 procurement-trust logic: CAS identity gating, strict product-form classification, price-noise filtering, required-purity checks, and public-price trust scoring.
- Adds supplier-specific parser profiles for the full curated supplier registry instead of relying only on generic scraping fallbacks.
- Adds exact public catalog match logic:
  - if the requested quantity is publicly listed, the app uses the listed price directly,
  - no extrapolation is used for an exact public pack match.
- Adds nearest-pack interpolation logic:
  - if the requested quantity falls between two public catalog packs, the app interpolates between those two rows,
  - if the requested quantity is above the public catalog ladder, the app then uses the v12/v13 scale-up estimator.
- Adds a Supplier Coverage CSV export showing which curated suppliers were checked, which parser profile ran, and whether the result was public-price parsed, login/account-gated, quote/RFQ-gated, skipped, or not parsed by the current profile.
- Updates live-mode defaults to walk the full curated supplier registry first.
- Improves wording from “no public price” to “No public price detected by current parser” where appropriate.

## Supplier parser coverage

v13 includes parser profiles for 35 curated sources, including TargetMol, MedChemExpress, SelleckChem, Cayman, MolPort, Adooq, ApexBio, GLP Bio, AbMole, ChemFaces, BioCrick, CSNpharm, InvivoChem, Biorbyt, TCI, Oakwood, Chem-Impex, Combi-Blocks, BLD Pharm, Ambeed, A2B Chem, Enamine, Matrix Scientific, Santa Cruz Biotechnology, CymitQuimica, Toronto Research Chemicals, Fisher, Thermo/Alfa, Sigma-Aldrich, VWR/Avantor, ChemicalBook, ChemBlink, ChemExper, and LookChem.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Suggested tests

- `487-41-2` with 25 mg, 75 mg, 500 mg, 50 g, and 1 kg to test exact-match, interpolation, and scale-up modes.
- `151-21-3` for public catalog behavior.
- `64-17-5` for commodity/log-in source behavior.

Visible catalog prices are evidence. Desired-quantity estimates are procurement models. Confirmed RFQ pricing is truth.
