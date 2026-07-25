"""Tests for the RK-BAKEOFF extractor bake-off harness (``eval.extraction``).

Everything here is offline and corpus-blind: fixtures are invented, the labeled inputs are synthesised in
``tmp_path`` against the schemas the harness declares, and no test opens the real corpus, the answer key,
the claim gold or the sub-oracle.
"""
