## 2023-10-27 - Deferring modulo in Python loops
**Learning:** Python handles large integers automatically without overflowing. In intensive algorithms like polynomial multiplication modulo N (`poly_mul`), performing `% N` inside a tight double loop introduces unnecessary overhead. By simply accumulating the sums and deferring the modulo operation to a single list comprehension at the end (`[x % N for x in res]`), we avoid Python bytecode overhead and see an observable speedup with zero risk of C-style overflow.
**Action:** In Python performance paths involving modulo arithmetic (especially polynomial/matrix operations), accumulate raw sums first and map modulo at the very end.

## 2023-10-27 - Binary exponentiation loop optimization
**Learning:** In standard binary exponentiation loops (`while exp > 0:`), the final iteration always computes a redundant square (`curr = curr * curr % N`) because `exp` is truncated to 0 right before it.
**Action:** Always wrap the final square operation in `if exp > 0:` after `exp //= 2` to skip an expensive multiplication/modulo that is immediately thrown away.

## 2024-05-24 - Deferring modulo in polynomial division
**Learning:** In polynomial division (`poly_divmod`), modulo operations inside the inner subtraction loop (`num[shift + i] = (num[shift + i] - coeff * den[i]) % N`) are computationally expensive. Since Python handles arbitrarily large integers automatically, we can safely defer the `% N` modulo operation until the very end. This reduces modulo operations from O(deg_num * deg_den) to O(deg_num) and avoids significant overhead.
**Action:** When implementing mathematical operations involving polynomial division or arrays in Python, defer the modulo operations outside tight inner loops unless dealing with a language with strict integer overflow limits.
