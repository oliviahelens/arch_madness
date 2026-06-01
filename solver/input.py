"""Puzzle transcriptions. Cells are 0-indexed (row, col), row 0 = top.

clues: {(r, c): score}
green: set of (r, c) where no arc may be placed
"""

# 4x4 worked example (ground truth: answer = 18928, scores 3,9,6,8,6,24)
EXAMPLE = {
    "N": 4,
    "clues": {
        (0, 0): 3, (0, 2): 9,
        (1, 3): 6,
        (2, 0): 8,
        (3, 1): 6, (3, 3): 24,
    },
    "green": {(0, 1), (0, 3), (2, 1), (2, 3)},
    "answer": 18928,
}

# 9x9 puzzle (TRANSCRIPTION — pending user confirmation).
PUZZLE = {
    "N": 9,
    "clues": {
        (0, 2): 21,
        (1, 0): 21, (1, 4): 27, (1, 7): 25,
        (2, 1): 27, (2, 5): 15, (2, 8): 9,
        (4, 0): 25, (4, 3): 27, (4, 5): 45, (4, 8): 9,
        (6, 0): 9, (6, 3): 63, (6, 7): 45,
        (7, 1): 63, (7, 4): 9, (7, 8): 288,
        (8, 5): 35,
    },
    "green": {
        (0, 0), (0, 3), (0, 5), (0, 7),
        (1, 3), (1, 6), (1, 8),
        (2, 0), (2, 7),
        (3, 8),
        (4, 0), (4, 4),
        (5, 7), (5, 8),
        (7, 0),
        (8, 1), (8, 4), (8, 8),
    },
}
