import cmath


def solve_quadratic(a: complex, b: complex, c: complex) -> list[complex]:
    """Solves a quadratic equation ax^2 + bx + c = 0."""
    discriminant = b**2 - 4 * a * c
    d_sqrt = cmath.sqrt(discriminant)
    return [(-b + d_sqrt) / (2 * a), (-b - d_sqrt) / (2 * a)]


def solve_cubic(a: float, b: float, c: float, d: float) -> list[complex]:
    """Solves a cubic equation ax^3 + bx^2 + cx + d = 0."""
    # Depress the cubic: x = y - b/(3a)
    # y^3 + py + q = 0
    p = (3 * a * c - b**2) / (3 * a**2)
    q = (2 * b**3 - 9 * a * b * c + 27 * a**2 * d) / (27 * a**3)

    discriminant = (q / 2) ** 2 + (p / 3) ** 3
    sqrt_disc = cmath.sqrt(discriminant)

    u_val = -q / 2 + sqrt_disc
    v_val = -q / 2 - sqrt_disc

    # We need the principal cube roots.
    u = u_val ** (1 / 3)
    v = v_val ** (1 / 3)

    # The three roots for y:
    omega = complex(-0.5, (3**0.5) / 2)
    y1 = u + v
    y2 = u * omega + v * (omega**2)
    y3 = u * (omega**2) + v * omega

    shift = b / (3 * a)
    return [y1 - shift, y2 - shift, y3 - shift]


def solve_quartic(a: float, b: float, c: float, d: float, e: float) -> list[complex]:
    """
    Solves a quartic equation ax^4 + bx^3 + cx^2 + dx + e = 0
    using Ferrari's method.
    """
    if a == 0:
        raise ValueError("The coefficient 'a' cannot be zero for a quartic equation.")

    # Normalize to x^4 + Ax^3 + Bx^2 + Cx + D = 0
    A = b / a
    B = c / a
    C = d / a
    D = e / a

    # Step 1: Depress the quartic equation by substituting x = y - A/4
    # This results in y^4 + py^2 + qy + r = 0
    p = B - (3 / 8) * A**2
    q = C - (A * B) / 2 + (A**3) / 8
    r = D - (A * C) / 4 + (A**2 * B) / 16 - (3 * A**4) / 256

    # Step 2: Solve the resolvent cubic for k:
    # 8k^3 - 4pk^2 - 8rk + (4pr - q^2) = 0
    c3 = 8
    c2 = -4 * p
    c1 = -8 * r
    c0 = 4 * p * r - q**2

    # We pick one root of the cubic.
    k_roots = solve_cubic(c3, c2, c1, c0)
    k = k_roots[0]

    # Step 3: Split the depressed quartic into two quadratics using k.
    # (y^2 + k)^2 = (2k - p)y^2 - qy + (k^2 - r)
    # Let S^2 = 2k - p.
    # The two quadratics are:
    # 1) y^2 - S*y + (k + q/(2*S)) = 0
    # 2) y^2 + S*y + (k - q/(2*S)) = 0

    S_sq = 2 * k - p
    if abs(S_sq) < 1e-15:
        # If 2k-p = 0, then q must be 0.
        # The equation is y^4 + py^2 + r = 0 where p=2k.
        roots_y2 = solve_quadratic(1, p, r)
        y_roots = []
        for ry in roots_y2:
            y_roots.append(cmath.sqrt(ry))
            y_roots.append(-cmath.sqrt(ry))
        return [y - A / 4 for y in y_roots]

    S = cmath.sqrt(S_sq)
    denom = 2 * S

    # Quad 1: y^2 - S*y + (k + q/(2*S)) = 0
    # Quad 2: y^2 + S*y + (k - q/(2*S)) = 0
    quad1 = solve_quadratic(1, -S, k + q / denom)
    quad2 = solve_quadratic(1, S, k - q / denom)

    y_roots = quad1 + quad2
    return [y - A / 4 for y in y_roots]


if __name__ == "__main__":
    # Example: x^4 - 10x^3 + 35x^2 - 50x + 24 = 0 (Roots: 1, 2, 3, 4)
    a_coeff, b_coeff, c_coeff, d_coeff, e_coeff = 1, -10, 35, -50, 24
    roots = solve_quartic(a_coeff, b_coeff, c_coeff, d_coeff, e_coeff)
    print(
        f"Roots of {a_coeff}x^4 + {b_coeff}x^3 + {c_coeff}x^2 + {d_coeff}x + {e_coeff} = 0 are:"
    )
    for r in roots:
        print(f"{r:.4f}")
