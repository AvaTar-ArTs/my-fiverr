# Synthetic test state

The bridge verifier creates an empty SQLite database in a temporary directory
for each run. It never reads or modifies a personal Seller OS database.

If fixtures are added later, they must be fictional and contain no Fiverr
credentials, buyer messages, personal contact data, or copied marketplace
content. Keep fixtures outside the canonical state directory and make tests
deterministic.
