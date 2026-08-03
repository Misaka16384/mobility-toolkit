## 2023-10-27 - Deferring modulo in Python loops
**Learning:** Python handles large integers automatically without overflowing. In intensive algorithms like polynomial multiplication modulo N (`poly_mul`), performing `% N` inside a tight double loop introduces unnecessary overhead. By simply accumulating the sums and deferring the modulo operation to a single list comprehension at the end (`[x % N for x in res]`), we avoid Python bytecode overhead and see an observable speedup with zero risk of C-style overflow.
**Action:** In Python performance paths involving modulo arithmetic (especially polynomial/matrix operations), accumulate raw sums first and map modulo at the very end.

## 2023-10-27 - Binary exponentiation loop optimization
**Learning:** In standard binary exponentiation loops (`while exp > 0:`), the final iteration always computes a redundant square (`curr = curr * curr % N`) because `exp` is truncated to 0 right before it.
**Action:** Always wrap the final square operation in `if exp > 0:` after `exp //= 2` to skip an expensive multiplication/modulo that is immediately thrown away.

## 2024-05-24 - Deferring modulo in polynomial division
**Learning:** In polynomial division (`poly_divmod`), modulo operations inside the inner subtraction loop (`num[shift + i] = (num[shift + i] - coeff * den[i]) % N`) are computationally expensive. Since Python handles arbitrarily large integers automatically, we can safely defer the `% N` modulo operation until the very end. This reduces modulo operations from O(deg_num * deg_den) to O(deg_num) and avoids significant overhead.
**Action:** When implementing mathematical operations involving polynomial division or arrays in Python, defer the modulo operations outside tight inner loops unless dealing with a language with strict integer overflow limits.
## 2024-07-17 - [C-Level Optimization For Multi-Argument Math Methods]
**Learning:** Manual list loops and `functools.reduce` over math functions like `lcm` or `gcd` are unexpectedly heavy bottlenecks in purely algorithmic workflows like the Grobner basis solver, despite being common Python idioms. `math.gcd` and `math.lcm` (since Python 3.9) accept *args directly and process natively in C.
**Action:** Always scan numeric arrays for loop-based mathematical reductions (LCM, GCD, Sum) and map them to their Python 3.9+ C-optimized native multi-argument counterparts.

## 2024-07-27 - [List Comprehension Overhead in Inner Loops]
**Learning:** Using `all()` with a generator expression (e.g., `all(combo[i] >= mg[i] for i in range(n))`) inside heavily nested loops over large bounding boxes is a major performance bottleneck due to generator instantiation overhead.
**Action:** Unroll such constructs into explicit `for/break/else` primitive loops in Python when executing mathematically intensive inner loops (like the divisibility checks in `count_quotient_size`), achieving orders of magnitude speedups.

## 2023-10-27 - GF(2) Polynomial Exponentiation Optimization

**Learning:** When dealing with polynomial arithmetic over GF(2) (characteristic 2), the "Freshman's Dream" identity \((A+B)^2 = A^2 + B^2\) allows polynomial squaring to be performed in \(O(N)\) time by simply doubling the exponents of all terms, instead of performing a full \(O(N^2)\) polynomial multiplication.
**Action:** Always look for algebraic identities that simplify operations in finite fields, especially characteristic 2 (GF(2) or binary), which can reduce time complexity from quadratic to linear.

## 2024-11-20 - Vectorizing NumPy Array Modulo Operations
**Learning:** Python loops executing NumPy operations row-by-row are significantly slower due to loop overhead. Using array masking (`mask = factors != 0`) and vectorizing column slices (`factors = arr[:, col] % p`) can yield a 3-4x speedup in dense array arithmetic.
**Action:** When performing matrix row-reductions over finite fields in NumPy, avoid Python-level `for` loops iterating over array rows. Always use vectorized operations utilizing boolean masks and broadcasting.

## 2024-11-20 - Bit Packing for GF(2) Matrix Math
**Learning:** For matrix operations over GF(2) in pure Python, nested loops or generator comprehensions (like `sum(a*b) % 2`) are slow due to interpretation overhead. Packing boolean rows into integers (`sum((val & 1) << i for i, val in enumerate(row))`) and using C-optimized bitwise operations (`(r & c).bit_count() & 1`) provides an order-of-magnitude (~10x) speedup. However, for simple 1D vector dot products, replacing generator comprehensions with explicit `for` loops is faster than bit-packing due to the initial packing overhead.
**Action:** When implementing dense matrix multiplication over GF(2) in Python, vectorize using integer bit-packing. For 1D vector reductions, prefer explicit `for` loops with an accumulator to avoid generator instantiation overhead.
