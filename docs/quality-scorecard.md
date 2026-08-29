# Quality scorecard

The release scores **91/100** against an **80/100** target. The authoritative score and hard gates
are in `quality/scorecard.json`.

| Category | Score | Main evidence |
| --- | ---: | --- |
| Functional contract | 24/25 | Four executable, versioned modules |
| Interface interoperability | 19/20 | Native contract preservation and runner discovery |
| Reliability and safety | 18/20 | Payload/time/record bounds and mock-first gating |
| Verification and performance | 13/15 | Unit tests, runtime smoke, benchmark, soak procedure |
| Security and supply chain | 8/10 | Constrained container and CI scanning |
| Documentation and usability | 9/10 | Target/input/output table and operations guide |

Extended real-hardware latency and multi-hour observations are intentionally unearned until a
specific vendor product is selected and tested.
