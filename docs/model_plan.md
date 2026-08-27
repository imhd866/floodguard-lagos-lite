# Model plan

Phase 1 uses the weighted rule model from the project guide. Live rainfall is the only dynamic input. Other factors are clearly marked prototype baselines so the app never implies unsupported precision.

The OSM milestone replaces two baselines when a live query succeeds. Waterway proximity decreases linearly from 1.0 at the nearest mapped water feature to 0.0 at the 1.5 km query boundary. Infrastructure exposure combines capped road (50%), school (30%), and market (20%) densities. If Overpass fails, the UI explicitly reports the fallback to the location baseline.

Phase 2 replaces baselines incrementally with measured features from OpenStreetMap, Copernicus DEM, WorldPop, and a licensed historical-water source. Every feature should retain its source, retrieval time, transformation, and quality flag.

An LLM may rewrite a computed advisory for clarity. It must not change the score, invent evidence, remove uncertainty language, or suppress the disclaimer. The deterministic template remains the fallback.
