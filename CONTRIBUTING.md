# Publishing one GEP status cut

The private GEP status owns completed engineering truth, and its merged
`docs/current-slice.md` owns live implementation authority. This repository
owns only the reviewed public projection. The website is a renderer and must
not infer new claims.

Do not copy the private status document or restore the retired raw mirror.

## Selection or completion procedure

1. Read the private GEP status and merged current-slice authority from its
   current `main` branch.
2. Run the read-only drift check:

   ```sh
   git -C /path/to/generalized_execution_platform show origin/main:docs/current-slice.md \
     | python3 scripts/review_private_status.py -
   ```

   A pending verdict is expected before editing when a new selection or
   completion has landed.
3. Update only the allowlisted fields in `status.json`:
   - `published_at`;
   - `reviewed_through`;
   - `current`;
   - `last_completed`;
   - selected completed milestones;
   - the bounded public position and claim ceiling.
4. For every newly reviewed private slice, make an explicit editorial decision:
   publish one bounded result or omit it from the selected public ledger. Never
   let a slice disappear merely because no decision was made.
5. Render and validate:

   ```sh
   python3 scripts/render_status.py --write
   python3 scripts/render_status.py
   python3 -m unittest discover -s tests -v
   git -C /path/to/generalized_execution_platform show origin/main:docs/current-slice.md \
     | python3 scripts/review_private_status.py -
   ```

6. Open one ordinary pull request. A reviewer checks both the positive claim
   and every affected nonclaim before merging.
7. After merge, require the live-readback workflow and inspect the website.
   Publication is complete only when the live current slice, last completed
   slice, new ledger entry, claim ceiling, and publication date agree.

## Failure law

- A merged-authority/public mismatch blocks publication.
- Invalid or non-generated public artifacts block publication.
- A failed live readback leaves the last valid site content in place and keeps
  the publication incomplete.
- Automation may prepare and validate a candidate. It must not invent result
  wording, broaden a claim, copy raw private content, or merge without review.

The scheduled live check needs no private-repository credential. A future
cross-repository detector may receive a dedicated read-only credential, but it
must only compare the public status coordinates used by
`review_private_status.py`; it must never mirror the private authority document.
