## Public-status publication

- [ ] I reviewed the current private GEP status from its `main` branch.
- [ ] `reviewed_through` equals the latest completed slice.
- [ ] `current.slice` is active and is not listed as completed.
- [ ] Every newly reviewed slice has an explicit publish-or-omit decision.
- [ ] Each published result states only the bounded implemented outcome.
- [ ] The claim ceiling was reconciled with the newly completed work.
- [ ] No private path, repository coordinate, review link, application-specific content, secret, dataset, or operator evidence crosses the boundary.
- [ ] `python3 scripts/render_status.py` passes.
- [ ] `python3 -m unittest discover -s tests -v` passes.

After merge, require the live readback workflow and inspect the rendered website before calling publication complete.
