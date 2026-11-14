# Video runtime implementation

The video pipeline uses the accepted MongoDB application database decision.
Concurrent core/API work is preserved; videos supplies explicit router and reader adapters.
Local CLI development uses a named SQLite fake job adapter; it is never selected
automatically in deployed code. Atlas and local fake share lease/fencing semantics.

Claude's raw Messages API is the alternative explicitly allowed by TRD section 6.
The worker owns a bounded structured-tool submission/validation/repair loop. No
personal Claude configuration, shell, arbitrary filesystem or external tools are
loaded. This smaller surface is appropriate for the two initial templates.
Custom scene modules are compiled and executed only inside the renderer container.

Live implementation narrowed the generated scene API to a clipped phase-animation
band. Two model-generated graph implementations drew incorrect/null-crossing links.
The root now always renders the tested subject-specific pointer diagram and code;
Claude generates scripts and event-driven presentation around it. This preserves
the visible linked-list algorithm rather than trusting arbitrary code to rederive
its semantics. Broader arbitrary custom diagrams from TRD P3 are not claimed as
validated; additional subjects need tested semantic components and appropriate slots.

The renderer is a standalone Node package with a renderer-local lockfile. No root
workspace/lockfile is created or changed; Adi can integrate it into the workspace.
It remains the same Remotion service, not an additional application service.

Local generated artifacts remain validating until human review. Fixture narration,
unverified voices, and synthetic backgrounds do not satisfy live acceptance.
