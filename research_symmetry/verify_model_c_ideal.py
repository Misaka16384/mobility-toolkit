import sympy as sp

# Define symbols
x, y, t, u = sp.symbols('x y t u')

# Relations
# We want to check modulo 2 (all coefficients in Z_2) and modulo (x*t - 1, y*u - 1).
# We can represent polynomials as Laurent polynomials in x and y by substituting t -> 1/x and u -> 1/y.
# Then we clear denominators and check if they are multiples of f3 = (1+x)*(1+y**2)*(1+y+y**2).

f3 = (1 + x) * (1 + y**2) * (1 + y + y**2)

# M2 generators
gens = [
    y**2 * t + t * u**2 + y**2 + y * t + t * u + u**2 + y + u,
    x * y**2 + x * u**2 + x * y + y**2 + x * u + u**2 + y + u,
    t * u**3 + t * u**2 + u**3 + y * t + u**2 + y + t + 1,
    x * u**3 + x * u**2 + u**3 + x * y + u**2 + x + y + 1
]

def to_laurent(expr):
    # Substitute t -> 1/x, u -> 1/y
    return expr.subs({t: 1/x, u: 1/y})

print("f3 expanded mod 2:", sp.expand(f3) % 2)

for i, g in enumerate(gens):
    g_laurent = sp.simplify(to_laurent(g))
    # Multiply by a power of x and y to clear denominators
    # Let's see the degree of denominator
    denom = sp.denom(g_laurent)
    num = sp.numer(g_laurent)
    # mod 2 expansion of numerator
    num_expanded = sp.expand(num) % 2
    
    # Check if num_expanded is divisible by f3 in Z_2[x, y]
    # We can perform division or check if quotient has integer coefficients (mod 2)
    q, r = sp.div(num_expanded, f3, domain='GF(2)')
    print(f"Generator {i+1}:")
    print(f"  Laurent: {g_laurent}")
    print(f"  Numerator (mod 2): {num_expanded}")
    print(f"  Remainder of numerator / f3 (mod 2): {r}")
    print(f"  Quotient: {q}")
    print()
