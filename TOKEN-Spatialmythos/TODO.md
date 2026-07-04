# TODO - Royalice folded merge/trace/re-merge compressed state

- [ ] Update `HashSpace` to support content-addressed folded storage (hash+data -> deduped payload)
- [ ] Implement merge+trace+re-merge routine that iteratively folds state until size stops improving (bounded rounds)
- [ ] Add integrity digest (single hash) computed over folded state
- [ ] Update `SaveHashSpaceSnapshot()` to persist only folded state + integrity digest (single file)
- [ ] Adjust `Program` main loop to call folding/merge routine after simulation (or periodically)
- [ ] Build and run `dotnet build` + `dotnet run -c Debug` and confirm output `hashes.json` is folded

