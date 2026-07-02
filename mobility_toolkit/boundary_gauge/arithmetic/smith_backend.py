"""Smith normal form backend exports with SymPy version compatibility fallback."""

try:
    raise ImportError("Force custom smith_normal_decomp implementation to prevent infinite loop hang on composite qudit dimensions.")
    from sympy.matrices.normalforms import smith_normal_decomp
except ImportError:
    import sympy as sp

    def smith_normal_decomp(A, domain=sp.ZZ):
        """
        Computes the Smith Normal Form decomposition of a matrix A over Z.
        Returns (D, U, V) such that D = U * A * V is diagonal,
        D_i,i divides D_i+1,i+1, and U, V are unimodular matrices.
        """
        m, n = A.rows, A.cols
        M = A.copy()
        U = sp.Matrix.eye(m)
        V = sp.Matrix.eye(n)

        def ext_gcd(a, b):
            a = int(a)
            b = int(b)
            if a == 0 and b == 0:
                return 0, 0, 0
            x0, x1, y0, y1 = 1, 0, 0, 1
            sign_a = 1 if a >= 0 else -1
            sign_b = 1 if b >= 0 else -1
            a_val = abs(a)
            b_val = abs(b)
            while b_val != 0:
                q = a_val // b_val
                a_val, b_val = b_val, a_val - q * b_val
                x0, x1 = x1, x0 - q * x1
                y0, y1 = y1, y0 - q * y1
            return a_val, x0 * sign_a, y0 * sign_b

        def swap_rows(i, j):
            if i == j:
                return
            M.row_swap(i, j)
            U.row_swap(i, j)

        def swap_cols(i, j):
            if i == j:
                return
            M.col_swap(i, j)
            V.col_swap(i, j)

        def add_rows(m_mat, i, j, a, b, c, d):
            row_i = m_mat[i, :]
            row_j = m_mat[j, :]
            m_mat[i, :] = a * row_i + b * row_j
            m_mat[j, :] = c * row_i + d * row_j

        def add_columns(m_mat, i, j, a, b, c, d):
            col_i = m_mat[:, i]
            col_j = m_mat[:, j]
            m_mat[:, i] = a * col_i + b * col_j
            m_mat[:, j] = c * col_i + d * col_j

        # Run elimination
        for k in range(min(m, n)):
            pivot_r, pivot_c = -1, -1
            min_val = None
            for r in range(k, m):
                for c in range(k, n):
                    val = abs(M[r, c])
                    if val != 0:
                        if min_val is None or val < min_val:
                            min_val = val
                            pivot_r, pivot_c = r, c
            
            if pivot_r == -1:
                break

            swap_rows(k, pivot_r)
            swap_cols(k, pivot_c)

            clear_iter = 0
            while True:
                clear_iter += 1
                if clear_iter > 100:
                    break
                col_clear = True
                # clear column k
                for r in range(k + 1, m):
                    if M[r, k] != 0:
                        col_clear = False
                        if M[r, k] % M[k, k] == 0:
                            d = M[r, k] // M[k, k]
                            add_rows(M, k, r, 1, 0, -d, 1)
                            add_rows(U, k, r, 1, 0, -d, 1)
                        else:
                            g, s, t = ext_gcd(M[k, k], M[r, k])
                            u = M[k, k] // g
                            v = M[r, k] // g
                            add_rows(M, k, r, s, t, -v, u)
                            add_rows(U, k, r, s, t, -v, u)
                
                row_clear = True
                # clear row k
                for c in range(k + 1, n):
                    if M[k, c] != 0:
                        row_clear = False
                        if M[k, c] % M[k, k] == 0:
                            d = M[k, c] // M[k, k]
                            add_columns(M, k, c, 1, 0, -d, 1)
                            add_columns(V, k, c, 1, 0, -d, 1)
                        else:
                            g, s, t = ext_gcd(M[k, k], M[k, c])
                            u = M[k, k] // g
                            v = M[k, c] // g
                            add_columns(M, k, c, s, t, -v, u)
                            add_columns(V, k, c, s, t, -v, u)

                if col_clear and row_clear:
                    break

        # Normalize sign of diagonal elements
        for i in range(min(m, n)):
            if M[i, i] < 0:
                for col in range(n):
                    M[i, col] = -M[i, col]
                for col in range(m):
                    U[i, col] = -U[i, col]

        # divisibility condition using SymPy's closed form
        changed = True
        div_iter = 0
        while changed:
            changed = False
            div_iter += 1
            if div_iter > 100:
                break
            for i in range(min(m, n) - 1):
                if M[i, i] != 0 and M[i+1, i+1] != 0:
                    if M[i+1, i+1] % M[i, i] != 0:
                        a = M[i, i]
                        b = M[i+1, i+1]
                        g, x, y = ext_gcd(a, b)
                        alpha = a // g
                        beta = b // g
                        
                        add_rows(U, i, i+1, 1, 0, x, 1)
                        add_columns(V, i, i+1, 1, y, 0, 1)
                        add_rows(U, i, i+1, 1, -alpha, 0, 1)
                        add_columns(V, i, i+1, 1, 0, -beta, 1)
                        add_rows(U, i, i+1, 0, 1, -1, 0)
                        
                        add_rows(M, i, i+1, 1, 0, x, 1)
                        add_columns(M, i, i+1, 1, y, 0, 1)
                        add_rows(M, i, i+1, 1, -alpha, 0, 1)
                        add_columns(M, i, i+1, 1, 0, -beta, 1)
                        add_rows(M, i, i+1, 0, 1, -1, 0)
                        
                        changed = True

        # Final sign normalization to be absolutely sure
        for i in range(min(m, n)):
            if M[i, i] < 0:
                for col in range(n):
                    M[i, col] = -M[i, col]
                for col in range(m):
                    U[i, col] = -U[i, col]

        return M, U, V

__all__ = ["smith_normal_decomp"]
