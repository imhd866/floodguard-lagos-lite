# Model plan

Phase 1 uses the weighted rule model from the project guide. Live rainfall is the only dynamic input. Other factors are clearly marked prototype baselines so the app never implies unsupported precision.

Phase 2 replaces baselines incrementally with measured features from OpenStreetMap, Copernicus DEM, WorldPop, and a licensed historical-water source. Every feature should retain its source, retrieval time, transformation, and quality flag.

An LLM may rewrite a computed advisory for clarity. It must not change the score, invent evidence, remove uncertainty language, or suppress the disclaimer. The deterministic template remains the fallback.
