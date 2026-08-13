import time
from mobility_toolkit.geometry.cell_complex import diagnose_cubical_mask
import itertools

top_cells = list(itertools.product(range(50), range(50), range(50)))

def diagnose_cubical_mask_zip_generator(top_cells):
    # This is basically the original, minus the setup differences
    cells = tuple(sorted(set(tuple(cell) for cell in top_cells)))
    dimension = len(cells[0])
    adjacency = {cell: set() for cell in cells}
    pinched = []
    cell_set = frozenset(cells)

    face_offsets = []
    pinched_offsets = []

    # Original setup
    for offset in itertools.product([-1, 0, 1], repeat=dimension):
        if all(o == 0 for o in offset):
            continue

        is_positive = False
        for o in offset:
            if o > 0:
                is_positive = True
                break
            elif o < 0:
                break

        if not is_positive:
            continue

        ones = sum(abs(o) == 1 for o in offset)
        if ones == 1:
            face_offsets.append(offset)
        else:
            pinched_offsets.append(offset)

    # Map operator.add
    import operator
    for left in cells:
        for offset in face_offsets:
            right = tuple(map(operator.add, left, offset))
            if right in cell_set:
                adjacency[left].add(right)
                adjacency[right].add(left)
        for offset in pinched_offsets:
            right = tuple(map(operator.add, left, offset))
            if right in cell_set:
                pinched.append((left, right))

    return

start = time.time()
diagnose_cubical_mask_zip_generator(top_cells)
end = time.time()
print(f"Map with operator.add time taken: {end - start:.2f}s")
