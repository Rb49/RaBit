import numpy as np
import queue


def floodfillNd(board: np.ndarray, background: int, color: int, *seed) -> None:
    directions = []
    seed = list(seed)
    for i in range(len(seed)):
        seedCopy = seed.copy()
        seedCopy[i] += 1
        directions.append(tuple(seedCopy))
        seedCopy = seed.copy()
        seedCopy[i] -= 1
        directions.append(tuple(seedCopy))

    for coords in directions:
        try:
            if board[coords] == background:
                board[coords] = color
                floodfillNd(board, background, color, *coords)
        except IndexError:
            continue


if __name__ == '__main__':
    arr = np.zeros((4, 4, 4, 4))
    arr[1:3, 1:3, 1:3, 1:3] = 1
    start = (0, 0, 0, 0)

    print('before:\n', arr)

    floodfillNd(arr, 0, 2, *start)

    print('after:\n', arr)
