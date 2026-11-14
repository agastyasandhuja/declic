# Enzyme animation source and visual contract

Source checked November 14, 2026:

- [OpenStax Biology 2e, 6.5 Enzymes](https://openstax.org/books/biology-2e/pages/6-5-enzymes): induced fit, active site, alternative substrate/product arrangements, catalyst reuse, competitive inhibition, and heat-induced denaturation.
- [NCATS Assay Guidance Manual, Mechanism of Action Assays for Enzymes](https://www.ncbi.nlm.nih.gov/books/NBK92001/): classical reversible competition, mutually exclusive substrate/inhibitor binding, and dependence on substrate concentration.

The fixture illustrates a cleavage reaction; it does not imply every enzyme cuts a molecule. The green joined shape represents one substrate and two green separated shapes represent its products. The coral shape is a reversible competitive inhibitor. Cyan is the enzyme throughout. Shapes, sizes, trajectories and times are schematic, not molecular simulation data.

`enzyme_hook`: an intact enzyme has its pocket occupied; substrate stops short.
`enzyme_fit`: a close-up of green substrate binding and both partners flexing.
`enzyme_reaction`: one bound substrate becomes two departing products.
`enzyme_reuse`: three staggered encounters with the same unchanged enzyme.
`enzyme_compete`: two approach paths converge; the inhibitor arrives first.
`enzyme_concentration`: qualitative low/high substrate comparison. The right-side inhibitor leaves *before* substrate binds; substrate does not knock it out.
`enzyme_denature`: inhibitor leaves the intact site, then excessive-heat cues accompany a deformed protein and no longer functional pocket. This is a contrasting mechanism, not a consequence of competitive binding.

No claims about measured reaction speed, molecular geometry, or inhibition constants are intended. Source attribution stays in accompanying metadata rather than a persistent video footer. The two external textbook diagrams are not copied; the SVG artwork is authored in this repository.
