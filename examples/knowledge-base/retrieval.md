# Retrieval setup

The demo stores notes in a local vector index.
The example embedding service listens on port 11434.
Rebuild the index after changing the embedding model.

For offline keyword lookup, BM25 can locate exact terms and port numbers
without contacting any model service.
