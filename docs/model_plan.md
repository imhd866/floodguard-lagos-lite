# Model plan

Phase 1 uses the weighted rule model from the project guide. Live rainfall is the only dynamic input. Other factors are clearly marked prototype baselines so the app never implies unsupported precision.

The OSM milestone replaces two baselines when a live query succeeds. Waterway proximity decreases linearly from 1.0 at the nearest mapped water feature to 0.0 at the 1.5 km query boundary. Infrastructure exposure combines capped road (50%), school (30%), and market (20%) densities. If Overpass fails, the UI explicitly reports the fallback to the location baseline.

Phase 2 replaced four baselines with measured features: OpenStreetMap supplies waterways
and infrastructure live; Copernicus DEM GLO-30 supplies surface elevation; and WorldPop 2020
supplies estimated population inside a 1.5 km circle.

Phase 3 replaces the final historical-water baseline with Digital Earth Africa WOfS all-time
frequency at 30 m resolution. The score uses the proportion of valid pixels in a 1.5 km circle
with at least 5% wet observations, capped at 25% affected area. This is a transparent screening
transform rather than a calibrated Lagos flood model. All cached features retain source,
retrieval time, transformation, and a validity measure.

An LLM may rewrite a computed advisory for clarity. It must not change the score, invent evidence, remove uncertainty language, or suppress the disclaimer. The deterministic template remains the fallback.

The NVIDIA NIM integration enforces that boundary by checking the rewritten output for the selected location, exact score, and complete responsible-use disclaimer. Failed API calls or failed checks return the deterministic draft.
