# Proof Mechanism Extractor Prompt

Extract reusable proof mechanisms from the paper text and theorem cards.

Build:

- proof_cards.json
- method_cards.json

Proof cards must include:

- theorem_label
- proof strategy
- key lemmas
- key estimates
- where assumptions are used
- possible fragile steps
- likely reusable tools

Method cards should include methods such as:

- De Giorgi iteration
- Caccioppoli inequality
- commutator estimate
- monotonicity formula
- epiperimetric inequality
- Modica gradient bound
- varifold compactness
- blow-up analysis
- Schauder estimate
- Li-Yau estimate
- Gamma-convergence

For each method include:

- where it appears
- what it proves
- what assumptions it needs
- how reusable it is

Mark uncertain extraction explicitly.
