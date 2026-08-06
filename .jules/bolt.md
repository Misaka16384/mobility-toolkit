## 2023-10-25 - GF(2) matrix multiplication packing
**Learning:** In Python, doing mathematical matrix multiplication for GF(2) with nested list comprehensions (or generators) `sum(a*b...) % 2` creates significant object instantiation overhead. Packing rows and columns into integers via bitshifts, and performing `(r & c).bit_count() & 1` is ~16x faster due to C-level execution of bitwise operations.
**Action:** Always prefer bit-packing into Python integers and native operations (`bit_count()`) when implementing matrix multiplication or large vector collections over Galois Field 2.
